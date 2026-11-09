-- Расширение для ограничения пересекающихся бронирований
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- 1. Пользователи

CREATE TABLE IF NOT EXISTS users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_users_role
        CHECK (role IN ('user', 'admin'))
);

-- 2. Категории помещений

CREATE TABLE IF NOT EXISTS categories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

-- 3. Помещения

CREATE TABLE IF NOT EXISTS rooms (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    room_number VARCHAR(30) NOT NULL UNIQUE,
    category_id BIGINT NOT NULL,
    capacity INTEGER NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_rooms_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT chk_rooms_capacity
        CHECK (capacity > 0)
);

-- 4. Бронирования

CREATE TABLE IF NOT EXISTS bookings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    purpose TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cancelled_at TIMESTAMPTZ,

    CONSTRAINT fk_bookings_room
        FOREIGN KEY (room_id)
        REFERENCES rooms(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_bookings_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT chk_bookings_time
        CHECK (end_time > start_time),

    CONSTRAINT chk_bookings_status
        CHECK (status IN ('active', 'cancelled')),

    CONSTRAINT chk_bookings_cancellation
        CHECK (
            (status = 'active' AND cancelled_at IS NULL)
            OR
            (status = 'cancelled' AND cancelled_at IS NOT NULL)
        ),

    -- Запрещаем пересекающиеся активные бронирования
    CONSTRAINT no_overlapping_active_bookings
        EXCLUDE USING GIST (
            room_id WITH =,
            tstzrange(start_time, end_time, '[)') WITH &&
        )
        WHERE (status = 'active')
);

-- 5. Журнал действий

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT,
    booking_id BIGINT,
    action VARCHAR(100) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_audit_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,

    CONSTRAINT fk_audit_booking
        FOREIGN KEY (booking_id)
        REFERENCES bookings(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- 6. Индексы для ускорения запросов

CREATE INDEX IF NOT EXISTS idx_rooms_category
    ON rooms(category_id);

CREATE INDEX IF NOT EXISTS idx_rooms_active
    ON rooms(is_active);

CREATE INDEX IF NOT EXISTS idx_bookings_room_time
    ON bookings(room_id, start_time, end_time);

CREATE INDEX IF NOT EXISTS idx_bookings_user
    ON bookings(user_id);

CREATE INDEX IF NOT EXISTS idx_bookings_status
    ON bookings(status);

CREATE INDEX IF NOT EXISTS idx_audit_created_at
    ON audit_log(created_at);

-- 7. Начальные категории помещений

INSERT INTO categories (name, description)
VALUES
    ('Учебные аудитории', 'Помещения для проведения учебных занятий'),
    ('Компьютерные классы', 'Помещения, оборудованные компьютерами'),
    ('Конференц-залы', 'Помещения для конференций и совещаний'),
    ('Лаборатории', 'Помещения для лабораторных и практических работ')
ON CONFLICT (name) DO NOTHING;