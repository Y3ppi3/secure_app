import sqlite3
from werkzeug.security import generate_password_hash

# Данные для нового тестового пользователя
email = "huy@eblan.com"
first_name = "huy@eblan.com"
password = "qwerty"
birthdate = "2000-01-01"

# Хешируем пароль с использованием метода 'pbkdf2:sha256'
hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
print(f"Метод хеширования пароля: 'pbkdf2:sha256'")
print(f"Хешированный пароль: {hashed_password}")

# Подключение к базе данных
DATABASE = 'users.db'


def add_test_user(email, first_name, hashed_password, birthdate):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Использование 'first_name' вместо 'full_name'
        cursor.execute("""
            INSERT INTO users (email, first_name, password, birthdate)
            VALUES (?, ?, ?, ?)
        """, (email, first_name, hashed_password, birthdate))

        conn.commit()
        print("Тестовый пользователь успешно добавлен!")
    except sqlite3.IntegrityError:
        print("Ошибка: пользователь с таким email уже существует.")
    finally:
        conn.close()
        print("Соединение с базой данных закрыто.")


# Добавляем тестового пользователя
add_test_user(email, first_name, hashed_password, birthdate)
