from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Для безопасности сессий

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# Инициализация базы данных
def init_db():
    with sqlite3.connect('users.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS markers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

init_db()

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        if not username or not password or role not in ['admin', 'user']:
            return "Invalid input", 400

        with get_db_connection() as conn:
            conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, password, role))
            conn.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()

        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials", 401

    return render_template('login.html')

# Выход
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Дашборд
@app.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session['role'] == 'admin':
        return redirect(url_for('admin'))
    elif session['role'] == 'user':
        return redirect(url_for('user'))

# Админская страница
@app.route('/admin')
def admin():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        markers = conn.execute('SELECT * FROM markers').fetchall()

    # Используем вспомогательную функцию
    markers = rows_to_dict(markers)

    return render_template('admin.html', markers=markers)

# Удаление метки (админ)
@app.route('/delete_marker/<int:marker_id>', methods=['POST'])
def delete_marker(marker_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return "Unauthorized", 403

    with get_db_connection() as conn:
        conn.execute('DELETE FROM markers WHERE id = ?', (marker_id,))
        conn.commit()

    return jsonify({"status": "success"})

# Пользовательская страница
@app.route('/user')
def user():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    return render_template('user.html')

# Добавление метки (пользователь)
@app.route('/add_marker', methods=['POST'])
def add_marker():
    if 'user_id' not in session or session['role'] != 'user':
        return "Unauthorized", 403

    lat = float(request.form['lat'])
    lon = float(request.form['lon'])

    with get_db_connection() as conn:
        conn.execute('INSERT INTO markers (lat, lon, created_at) VALUES (?, ?, datetime("now"))', (lat, lon))
        conn.commit()

    return jsonify({"status": "success"})

# Прокладка маршрута (админ)
@app.route('/route', methods=['POST'])
def route():
    if 'user_id' not in session or session['role'] != 'admin':
        return "Unauthorized", 403

    start = request.form.get('start')
    end = request.form.get('end')

    if not start or not end:
        return jsonify({"status": "error", "message": "Both start and end points are required"}), 400

    return jsonify({"status": "success", "route": {"start": start, "end": end}})


# Вспомогательная функция для преобразования Row в словарь
def rows_to_dict(rows):
    return [dict(row) for row in rows]


if __name__ == '__main__':
    app.run(debug=True)