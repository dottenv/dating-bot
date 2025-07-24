from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "tg_id" BIGINT NOT NULL UNIQUE,
    "username" VARCHAR(64),
    "registered_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "is_active" INT NOT NULL  DEFAULT 1,
    "rating" INT NOT NULL  DEFAULT 100
);
CREATE TABLE IF NOT EXISTS "profile" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "first_name" VARCHAR(64) NOT NULL,
    "last_name" VARCHAR(64),
    "age" INT,
    "city" VARCHAR(64),
    "about" TEXT,
    "tags" VARCHAR(256),
    "gender" VARCHAR(16),
    "orientation" VARCHAR(32),
    "dating_goal" VARCHAR(64),
    "profile_completed" INT NOT NULL  DEFAULT 0,
    "user_id" INT NOT NULL UNIQUE REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
