from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
DB_NAME = "Movie_Review.db"
REVIEWS_PER_PAGE = 10

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DB_NAME):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute('''CREATE TABLE genres (genre_id INTEGER PRIMARY KEY AUTOINCREMENT, genre_name TEXT NOT NULL UNIQUE)''')
        cursor.execute('''CREATE TABLE directors (director_id INTEGER PRIMARY KEY AUTOINCREMENT, director_name TEXT NOT NULL, nationality TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE movies (movie_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, release_year INTEGER NOT NULL, genre_id INTEGER, director_id INTEGER, FOREIGN KEY (genre_id) REFERENCES genres(genre_id), FOREIGN KEY (director_id) REFERENCES directors(director_id))''')
        cursor.execute('''CREATE TABLE users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, email TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE reviews (review_id INTEGER PRIMARY KEY AUTOINCREMENT, review_text TEXT NOT NULL, rating INTEGER CHECK(rating >= 1 AND rating <= 5), review_date DATE DEFAULT CURRENT_DATE, movie_id INTEGER, user_id INTEGER, FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE, FOREIGN KEY (user_id) REFERENCES users(user_id))''')

        cursor.executemany("INSERT INTO genres (genre_name) VALUES (?)", [("Action",),("Sci-Fi",),("Drama",),("Comedy",),("Horror",),("Romance",),("Thriller",),("Fantasy",),("Animation",),("Mystery",)])
        cursor.executemany("INSERT INTO directors (director_name, nationality) VALUES (?, ?)", [("Christopher Nolan","British"),("Steven Spielberg","American"),("Quentin Tarantino","American"),("Bong Joon Ho","Korean"),("Makoto Shinkai","Japanese"),("James Cameron","Canadian"),("Martin Scorsese","American"),("Guillermo del Toro","Mexican"),("Hayao Miyazaki","Japanese"),("Denis Villeneuve","Canadian")])
        cursor.executemany("INSERT INTO movies (title, release_year, genre_id, director_id) VALUES (?, ?, ?, ?)", [("Inception",2010,2,1),("Interstellar",2014,2,1),("Parasite",2019,7,4),("Your Name",2016,9,5),("Avatar",2009,2,6),("Spirited Away",2001,9,9),("Dune",2021,2,10),("Titanic",1997,6,6),("Pulp Fiction",1994,1,3),("Shutter Island",2010,10,7)])
        cursor.executemany("INSERT INTO users (username, email) VALUES (?, ?)", [(f"User_{i}", f"user{i}@email.com") for i in range(1,11)])
        cursor.executemany("INSERT INTO reviews (review_text, rating, movie_id, user_id) VALUES (?, ?, ?, ?)", [("หนังดีมาก เนื้อเรื่องล้ำยุคและหักมุมสุดๆ",5,1,1),("ภาพสวยตระการตา เพลงประกอบไพเราะกินใจ",5,2,2),("สะท้อนสังคมได้ยอดเยี่ยม สมมงรางวัลออสการ์",4,3,3),("อนิเมชั่นในดวงใจ ดูซ้ำกี่รอบก็ร้องไห้",5,4,4),("เอฟเฟกต์อลังการมาก แต่เนื้อเรื่องเดาทางง่ายไปหน่อย",3,5,5),("คลาสสิกตลอดกาล ลึกซึ้งและมีความหมาย",5,6,6),("งานสร้างยิ่งใหญ่ตระการตา รอดูภาคต่อเลย",4,7,7),("โรแมนติกดราม่าที่เศร้าและตราตรึงใจมาก",5,8,8),("บทกวนๆ สไตล์ผู้กำกับ ดำเนินเรื่องสนุกสะใจ",4,9,9),("หักมุมจนหัวหมุน บรรยากาศหนังสยองขวัญดีมาก",4,10,10)])
        conn.commit()
        conn.close()

init_db()

def build_filter_params(args):
    """รวบรวม filter params ทั้งหมดจาก request.args หรือ dict"""
    return {
        'movie_id':    args.get('movie_id',    ''),
        'user_id':     args.get('user_id',     ''),
        'genre_id':    args.get('genre_id',    ''),
        'director_id': args.get('director_id', ''),
        'rating':      args.get('rating',      ''),
        'year':        args.get('year',         ''),
        'page':        args.get('page',         1),
    }

@app.route('/')
def index():
    f = build_filter_params(request.args)
    page = int(f['page']) if str(f['page']).isdigit() else 1
    if page < 1:
        page = 1

    conn = get_db_connection()

    conditions, params = [], []

    if f['movie_id']:
        conditions.append("r.movie_id = ?");    params.append(f['movie_id'])
    if f['user_id']:
        conditions.append("r.user_id = ?");     params.append(f['user_id'])
    if f['genre_id']:
        conditions.append("m.genre_id = ?");    params.append(f['genre_id'])
    if f['director_id']:
        conditions.append("m.director_id = ?"); params.append(f['director_id'])
    if f['rating']:
        conditions.append("r.rating = ?");      params.append(f['rating'])
    if f['year']:
        conditions.append("m.release_year = ?");params.append(f['year'])

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    base_query = f"""
        FROM reviews r
        LEFT JOIN movies   m ON r.movie_id    = m.movie_id
        LEFT JOIN users    u ON r.user_id     = u.user_id
        LEFT JOIN genres   g ON m.genre_id    = g.genre_id
        LEFT JOIN directors d ON m.director_id = d.director_id
        {where_clause}
    """

    total_count = conn.execute(f"SELECT COUNT(*) {base_query}", params).fetchone()[0]
    total_pages = max(1, (total_count + REVIEWS_PER_PAGE - 1) // REVIEWS_PER_PAGE)
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * REVIEWS_PER_PAGE

    reviews_list = conn.execute(f"""
        SELECT r.review_id, r.review_text, r.rating, r.review_date,
               m.title, m.release_year, u.username, g.genre_name, d.director_name,
               r.movie_id, r.user_id, m.genre_id, m.director_id
        {base_query}
        ORDER BY r.review_id DESC
        LIMIT ? OFFSET ?
    """, params + [REVIEWS_PER_PAGE, offset]).fetchall()

    movies_list    = conn.execute('SELECT * FROM movies ORDER BY title').fetchall()
    users_list     = conn.execute('SELECT * FROM users ORDER BY username').fetchall()
    genres_list    = conn.execute('SELECT * FROM genres ORDER BY genre_name').fetchall()
    directors_list = conn.execute('SELECT * FROM directors ORDER BY director_name').fetchall()

    # ดึงปีที่มีอยู่จริงในฐานข้อมูล
    years_list = conn.execute(
        'SELECT DISTINCT release_year FROM movies ORDER BY release_year DESC'
    ).fetchall()

    conn.close()

    return render_template(
        'index.html',
        reviews=reviews_list,
        movies=movies_list,
        users=users_list,
        genres=genres_list,
        directors=directors_list,
        years=years_list,
        current_page=page,
        total_pages=total_pages,
        total_count=total_count,
        per_page=REVIEWS_PER_PAGE,
        # ค่า filter ที่เลือกอยู่
        sel_movie=f['movie_id'],
        sel_user=f['user_id'],
        sel_genre=f['genre_id'],
        sel_director=f['director_id'],
        sel_rating=f['rating'],
        sel_year=f['year'],
    )

def _filter_redirect_args(form):
    """สร้าง dict สำหรับ redirect หลัง update/delete โดยคง filter"""
    return dict(
        movie_id    = form.get('filter_movie_id',    ''),
        user_id     = form.get('filter_user_id',     ''),
        genre_id    = form.get('filter_genre_id',    ''),
        director_id = form.get('filter_director_id', ''),
        rating      = form.get('filter_rating',      ''),
        year        = form.get('filter_year',        ''),
        page        = form.get('page', 1),
    )

def get_or_create_user(conn, username: str) -> int:
    """คืน user_id — ถ้าชื่อซ้ำใช้ user เดิม ถ้าใหม่สร้างอัตโนมัติ"""
    username = username.strip()
    # INSERT OR IGNORE เพื่อไม่ให้ error เมื่อชื่อซ้ำ (UNIQUE constraint)
    conn.execute(
        "INSERT OR IGNORE INTO users (username, email) VALUES (?, ?)",
        (username, f"{username.lower().replace(' ', '_')}@auto.local")
    )
    row = conn.execute(
        "SELECT user_id FROM users WHERE username = ?", (username,)
    ).fetchone()
    return row["user_id"]


@app.route('/create', methods=['POST'])
def create():
    username    = request.form.get('username_input', '').strip()
    review_text = request.form['review_text']
    rating      = request.form['rating']
    movie_id    = request.form['movie_id']

    if not username:
        return redirect(url_for('index'))

    conn = get_db_connection()
    user_id = get_or_create_user(conn, username)
    conn.execute(
        'INSERT INTO reviews (review_text, rating, movie_id, user_id) VALUES (?, ?, ?, ?)',
        (review_text, rating, movie_id, user_id)
    )
    conn.commit(); conn.close()
    return redirect(url_for('index'))

@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    conn = get_db_connection()
    conn.execute(
        'UPDATE reviews SET review_text = ?, rating = ? WHERE review_id = ?',
        (request.form['review_text'], request.form['rating'], id)
    )
    conn.commit(); conn.close()
    return redirect(url_for('index', **_filter_redirect_args(request.form)))

@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM reviews WHERE review_id = ?', (id,))
    conn.commit(); conn.close()
    return redirect(url_for('index', **_filter_redirect_args(request.args)))

if __name__ == '__main__':
    app.run(debug=True)
