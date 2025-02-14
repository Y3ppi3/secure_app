from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime, date
import sqlite3
import requests
import os
import re

# Загрузка конфигурации из .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
SECRET_KEY = os.getenv('CloudFlare_SECRET_KEY')
DATABASE = os.getenv('DATABASE_URL').replace("sqlite:///", "")

# Инициализация объекта LoginManager
login_manager = LoginManager()
login_manager.init_app(app)  # Связываем LoginManager с Flask-приложением
login_manager.login_view = 'login' # Устанавливаем маршрут для редиректа, если пользователь не авторизован


# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Инициализация базы данных
def init_db():
    try:
        if not os.path.exists(DATABASE):
            conn = get_db_connection()
            with open('schema.sql') as f:
                conn.executescript(f.read())
            conn.close()
            print("Database initialized successfully.")
        else:
            print("Database already exists.")
    except FileNotFoundError:
        print("Error: 'schema.sql' file not found. Ensure it exists in the project directory.")
    except sqlite3.Error as e:
        print(f"Error initializing the database: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()


class User(UserMixin):
    def __init__(self, id, full_name, email):
        self.id = id
        self.full_name = full_name
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT id, full_name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(id=user["id"], full_name=user["full_name"], email=user["email"])
    return None

# Middleware для проверки капчи
@app.before_request
def ensure_captcha_verified():
    if request.endpoint in ['verify_captcha', 'static', 'login', 'register', 'reset_password']: ## — проверяется, является ли текущий запрос одним из тех, что не требует проверки капчи. Эти эндпоинты (verify_captcha, static, login, register, reset_password) исключаются из проверки, так как их функционал не зависит от прохождения капчи.
        return

    if not current_user.is_authenticated and not session.get('captcha_verified'):
        return redirect(url_for('verify_captcha'))


# Маршрут проверки капчи
@app.route('/verify', methods=['GET', 'POST'])
def verify_captcha():
    if request.method == 'GET':
        return render_template('verify.html')

    token = request.form.get('cf-turnstile-response')
    if not token:
        flash('Капча не заполнена.', 'error')
        return redirect(url_for('verify_captcha'))

    # Проверка капчи через Cloudflare Turnstile API
    response = requests.post(
        'https://challenges.cloudflare.com/turnstile/v0/siteverify',
        data={
            'secret': SECRET_KEY,
            'response': token,
        }
    )
    result = response.json()

    if result.get('success'):
        # Если капча пройдена успешно, пропускаем пользователя дальше
        session['captcha_verified'] = True
        return redirect(url_for('login')) # Перенаправляем на страницу логина (или другую)
    else:
        flash('Капча не пройдена. Пожалуйста, попробуйте снова.', 'error')
        return redirect(url_for('verify_captcha')) # Оставляем на странице с капчей

# Остальные маршруты
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']

        # Проверка на пустые поля
        if not email or not password:
            flash('Пожалуйста, заполните все поля.', 'error')
            return render_template('login.html')

        try:
            # Использование контекстного менеджера для работы с БД
            with get_db_connection() as conn:
                # Получаем пользователя по email
                user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

            if user and check_password_hash(user['password'], password):
                # Создание объекта пользователя
                user_obj = User(id=user['id'], full_name=user['full_name'], email=user['email'])
                login_user(user_obj)
                flash('Вход выполнен успешно!', 'success')
                return redirect(url_for('dashboard'))

            # Если пользователь не найден или пароль неверный
            flash('Неверные учетные данные. Попробуйте снова.', 'error')
            return render_template('login.html')

        except sqlite3.Error as e:
            # Обработка ошибок БД
            flash(f'Ошибка базы данных: {e}', 'error')
            return render_template('login.html')

    # Возвращаем страницу логина для GET-запроса
    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        address = request.form['address']
        service_type = request.form['service_type']
        service_date = request.form['service_date']
        service_time = request.form['service_time']

        # Валидация
        if not all([address, service_type, service_date, service_time]):
            flash('Все поля обязательны для заполнения!', 'error')
            return redirect(url_for('dashboard'))

        # Сохранение заявки
        try:
            with get_db_connection() as conn:
                conn.execute(""" 
                            INSERT INTO requests (user_id, address, service_type, service_date, service_time)
                            VALUES (?, ?, ?, ?, ?)
                        """, (current_user.id, address, service_type, service_date, service_time))
                conn.commit()
            flash('Заявка успешно создана!', 'success')
        except sqlite3.Error as e:
            flash(f'Ошибка при сохранении заявки: {e}', 'error')

        return redirect(url_for('dashboard'))

    # Получение заявок конкретного пользователя
    try:
        with get_db_connection() as conn:
            # Обновление статуса "pending" на "В ожидании"
            conn.execute("""
                    UPDATE requests
                    SET status = ?
                    WHERE status = ?
                """, ('В ожидании', 'pending'))
            conn.commit()

        # Получение всех заявок пользователя
            requests = conn.execute("""
                        SELECT address, service_type, service_date, service_time, status
                        FROM requests
                        WHERE user_id = ?
                        ORDER BY created_at DESC
            """, (current_user.id,)).fetchall()
    except sqlite3.Error as e:
        flash(f'Ошибка при получении заявок: {e}', 'error')
        requests = []  # Пустой список, если ошибка

    return render_template('dashboard.html', user_name=current_user.full_name, requests=requests)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    errors = {}  # Словарь для хранения ошибок

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        birth_day = request.form.get('birth_day', '').strip()
        birth_month = request.form.get('birth_month', '').strip()
        birth_year = request.form.get('birth_year', '').strip()

        # Валидация ФИО
        if not full_name:
            errors['full_name'] = 'Введите ваше ФИО.'
        elif any(char.isdigit() for char in full_name):
            errors['full_name'] = 'ФИО не может содержать цифры.'

        # Проверка даты рождения
        try:
            birthdate = datetime.strptime(f"{birth_year}-{birth_month}-{birth_day}", "%Y-%m-%d").date()
            # Проверка возраста (18+)
            today = date.today()
            age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
            if age < 18:
                errors['birthdate'] = 'Регистрация доступна только пользователям старше 18 лет.'
        except ValueError:
            errors['birthdate'] = 'Некорректная дата рождения. Проверьте введенные значения.'

        # Проверка email
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_pattern, email):
            errors['email'] = 'Некорректный адрес электронной почты.'

        # Проверка номера телефона
        phone_pattern = r'^\+?[\d\s-]{7,15}$'
        if not re.match(phone_pattern, phone):
            errors['phone'] = 'Некорректный номер телефона.'

        # Проверка пароля
        if not password:
            errors['password'] = 'Введите пароль.'
        elif len(password) < 8:
            errors['password'] = 'Пароль должен содержать не менее 8 символов.'

        # Если ошибок нет, продолжаем сохранение в базе
        if not errors:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            # Подключение к базе данных
            conn = get_db_connection()
            try:
                # Вставка данных пользователя
                conn.execute("""
                    INSERT INTO users (full_name, email, phone, password, birthdate)
                    VALUES (?, ?, ?, ?, ?)
                """, (full_name, email, phone, hashed_password, birthdate))
                conn.commit()
                flash('Регистрация успешна! Теперь войдите в свой аккаунт.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                errors['email'] = 'Эта электронная почта уже зарегистрирована.'
            finally:
                conn.close()

    # Передача ошибок в шаблон
    return render_template('register.html', errors=errors)



@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        flash('Инструкция по восстановлению пароля отправлена на указанный email.')
        return render_template('reset_password.html', email_sent=True)
    return render_template('reset_password.html', email_sent=False)


@app.route('/user_list')
def user_list():
    # Проверка сессии администратора
    if 'admin_id' not in session:
        flash('Пожалуйста, войдите как администратор.', 'error')
        return redirect(url_for('admin_login'))

    # Получение данных о пользователях для отображения
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()

    # Преобразование данных в список словарей
    users_list = [dict(user) for user in users]

    return render_template('user_list.html', users=users_list)

# Админский маршрут
@app.route('/adm_login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Подключение к БД и проверка учетных данных администратора
        conn = get_db_connection()
        admin = conn.execute('SELECT * FROM admin_users WHERE username = ?', (username,)).fetchone()
        conn.close()

        # Сравнение введенного пароля с хэшем в БД
        if admin and check_password_hash(admin['password'], password):
            session['admin_id'] = admin['id']
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('admin_panel'))
        else:
            error = 'Неправильное имя пользователя или пароль'
    return render_template('admin_login.html', error=error)


def fetch_users_from_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name, email, phone, birthdate FROM users")
    users = cursor.fetchall()
    conn.close()
    return users


def fetch_services_from_db():
    conn = get_db_connection()
    services = conn.execute("""
        SELECT id, user_id, address, service_type, service_date, service_time, status
        FROM requests
    """).fetchall()
    conn.close()
    return [dict(service) for service in services]


@app.route('/admin_panel', methods=['GET', 'POST'])
def admin_panel():
    # Проверка сессии администратора
    if 'admin_id' not in session:
        flash('Пожалуйста, войдите как администратор.', 'error')
        return redirect(url_for('admin_login'))

    # Получение фильтра статуса, по умолчанию "В ожидании"
    status_filter = request.args.get('status', 'В ожидании')

    try:
        # Подключение к базе данных
        conn = get_db_connection()

        # Получение списка пользователей
        users_list = conn.execute("SELECT * FROM users").fetchall()

        # Получение заявок с фильтрацией по статусу
        if status_filter:
            services_list = conn.execute("""
                SELECT id, user_id, address, service_type, service_date, service_time, status
                FROM requests
                WHERE status = ?
            """, (status_filter,)).fetchall()
        else:
            services_list = conn.execute("""
                SELECT id, user_id, address, service_type, service_date, service_time, status
                FROM requests
            """).fetchall()

        conn.close()

    except sqlite3.Error as e:
        flash(f'Ошибка при загрузке данных из базы: {e}', 'error')
        users_list = []
        services_list = []

    # Рендер страницы
    return render_template(
        'admin_panel.html',
        users=users_list,
        services=services_list,
        status_filter=status_filter
    )


@app.route('/update_service_status/<int:service_id>', methods=['POST'])
def update_service_status(service_id):
    action = request.form.get('action')

    # Подключаемся к базе данных
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if action == 'approve':
        # Подтверждение заявки
        cursor.execute('UPDATE requests SET status = "Одобрено" WHERE id = ?', (service_id,))
    elif action == 'reject':
        # Отклонение заявки
        cursor.execute('UPDATE requests SET status = "Отклонено" WHERE id = ?', (service_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('admin_panel'))


@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_id', None)
    flash('Вы вышли из системы администратора.', 'success')
    return redirect(url_for('admin_login'))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
