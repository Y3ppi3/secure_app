import sqlite3
from werkzeug.security import generate_password_hash

# Укажите путь к вашей базе данных
DATABASE = 'users.db'  # Укажите реальный путь к вашей базе данных

def create_admin(username, password):
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS admin_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)')
        conn.execute('INSERT INTO admin_users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        print(f"Администратор с логином '{username}' успешно создан.")
    except sqlite3.IntegrityError:
        print(f"Ошибка: Логин '{username}' уже существует.")
    finally:
        conn.close()

if __name__ == '__main__':
    admin_username = input("Введите логин для администратора: ")
    admin_password = input("Введите пароль для администратора: ")
    create_admin(admin_username, admin_password)
