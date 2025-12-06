```mermaid
erDiagram
    USERS {
        BIGINT user_id PK "ID пользователя Telegram"
        VARCHAR username "Никнейм"
        TIMESTAMP created_at "Дата регистрации"
    }

    PROFILES {
        SERIAL profile_id PK "ID анкеты"
        BIGINT user_id FK "Ссылка на пользователя"
        VARCHAR name "Имя"
        INT age "Возраст"
        ENUM gender "Пол"
        VARCHAR photo_url "Фото"
        ENUM communication_type "Тип общения"
        BOOLEAN verified "Верификация"
        TIMESTAMP created_at "Дата создания"
    }

    LIKES {
        SERIAL id PK "ID лайка"
        BIGINT from_user_id FK "Кто поставил"
        BIGINT to_user_id FK "Кому"
        TIMESTAMP created_at "Дата"
    }

    MATCHES {
        SERIAL match_id PK "ID матча"
        BIGINT user1_id FK "Первый пользователь"
        BIGINT user2_id FK "Второй пользователь"
        TIMESTAMP created_at "Дата совпадения"
    }

    %% Связи
    USERS ||--o{ PROFILES : ""
    USERS ||--o{ LIKES : ""
    USERS ||--o{ MATCHES : ""