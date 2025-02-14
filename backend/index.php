<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");

$requestBody = file_get_contents("php://input");
$data = json_decode($requestBody, true);

// Функция для проверки формата email
function validate_email($email) {
    return filter_var($email, FILTER_VALIDATE_EMAIL) && preg_match('/\.(com|ru|net|org|info)$/i', $email);
}

// Функция для проверки формата телефона
function validate_phone($phone) {
    // Убираем все лишние символы, оставляя только цифры и '+'
    $cleaned_phone = preg_replace('/[^\d+]/', '', $phone);

    // Проверяем формат (например, российский, американский и другие)
    return preg_match('/^\+7\d{10}$|^8\d{10}$|^\+1\d{10}$/', $cleaned_phone);
}

// Функция для проверки имени
function validate_full_name($full_name) {
    return preg_match('/^[\p{L} .\'-]+$/u', $full_name);
}

if (!empty($data['full_name']) && !empty($data['email_or_phone']) && !empty($data['password']) && !empty($data['confirm_password'])) {
    $full_name = trim($data['full_name']);
    $email_or_phone = trim($data['email_or_phone']);
    $password = $data['password'];
    $confirm_password = $data['confirm_password'];

    // Проверка имени
    if (!validate_full_name($full_name)) {
        echo json_encode(["message" => "Некорректное имя. Имя может содержать только буквы, пробелы и дефисы."]);
        exit;
    }

    // Проверка подтверждения пароля
    if ($password !== $confirm_password) {
        echo json_encode(["message" => "Пароли не совпадают."]);
        exit;
    }

    // Валидация email или телефона
    if (validate_email($email_or_phone)) {
        $contact_type = "email";
    } elseif (validate_phone($email_or_phone)) {
        $contact_type = "phone";
    } else {
        echo json_encode(["message" => "Некорректный email или номер телефона."]);
        exit;
    }

    // Хеширование пароля
    $hashed_password = password_hash($password, PASSWORD_BCRYPT);

    // Подключение к базе данных SQLite
    try {
        $db = new PDO('sqlite:your_database_path.db');
        $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        // Проверка уникальности email/телефона
        $stmt_check = $db->prepare("SELECT COUNT(*) FROM users WHERE email_or_phone = :email_or_phone");
        $stmt_check->bindParam(':email_or_phone', $email_or_phone);
        $stmt_check->execute();
        $exists = $stmt_check->fetchColumn();

        if ($exists) {
            echo json_encode(["message" => "Этот email или номер телефона уже зарегистрирован."]);
            exit;
        }

        // Вставка данных
        $stmt = $db->prepare("INSERT INTO users (full_name, email_or_phone, password) VALUES (:full_name, :email_or_phone, :password)");
        $stmt->bindParam(':full_name', $full_name);
        $stmt->bindParam(':email_or_phone', $email_or_phone);
        $stmt->bindParam(':password', $hashed_password);

        if ($stmt->execute()) {
            echo json_encode([
                "message" => "Регистрация прошла успешно!",
                "data" => [
                    "full_name" => $full_name,
                    "contact_type" => $contact_type,
                ]
            ]);
        } else {
            echo json_encode(["message" => "Ошибка при сохранении данных."]);
        }
    } catch (PDOException $e) {
        echo json_encode(["message" => "Ошибка базы данных: " . $e->getMessage()]);
    }
} else {
    echo json_encode(["message" => "Ошибка: все поля должны быть заполнены."]);
}
?>
