-- Назначение существующего пользователя администратором.
-- Замените CHANGE_ME на точный username зарегистрированного пользователя.
-- Если пользователь не найден, запрос вернёт 0 строк и никого не изменит.

WITH promoted_user AS (
    UPDATE users
    SET role = 'admin'
    WHERE username = 'CHANGE_ME'
    RETURNING id, username, full_name, role, created_at
)
SELECT *
FROM promoted_user;
