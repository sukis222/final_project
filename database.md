```mermaid
erDiagram
    USERS {
        INTEGER id PK
        BIGINT tg_id
        TEXT name
        INTEGER age
        TEXT gender
        TEXT photo_file_id
        TEXT goal
        TEXT description
        BOOLEAN is_active
        TIMESTAMP created_at
    }

    LIKES {
        INTEGER id PK
        INTEGER from_user_id
        INTEGER to_user_id
        BOOLEAN is_mutual
        TIMESTAMP created_at
    }

    MODERATION {
        INTEGER id PK
        INTEGER user_id
        TEXT photo_file_id
        TEXT status
        TIMESTAMP created_at
    }

    USERS ||--o{ LIKES : from_user
    USERS ||--o{ LIKES : to_user
    USERS ||--o{ MODERATION : moderation
