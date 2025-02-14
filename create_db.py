import sqlite3

# Название файла базы данных
DATABASE = 'users.db'

# Подключение к базе данных (если файл не существует, он будет создан)
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

# Создание таблицы пользователей с нужными полями
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone INTEGER UNIQUE NOT NULL,
    password TEXT NOT NULL,
    birthdate DATE
)
""")

# Создание таблицы заявок с добавленным статусом
cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    address TEXT NOT NULL,
    service_type TEXT NOT NULL,
    service_date DATE NOT NULL,
    service_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (user_id) REFERENCES users (id)
)
""")

# Создание таблицы администраторов
cursor.execute("""
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL
)
""")

# Закрытие соединения с базой данных
conn.commit()
conn.close()

print("База данных и таблицы 'users', 'requests' и 'admin_users' успешно созданы.")
