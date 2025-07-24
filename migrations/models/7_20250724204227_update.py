from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "adclick" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "button_text" VARCHAR(128) NOT NULL,
    "clicked_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "ad_id" INT NOT NULL REFERENCES "advertisement" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "advertisement" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "title" VARCHAR(128) NOT NULL,
    "text" TEXT NOT NULL,
    "media_type" VARCHAR(16),
    "media_file_id" VARCHAR(256),
    "buttons" JSON NOT NULL,
    "audience" VARCHAR(16) NOT NULL  DEFAULT 'all',
    "rounds" INT NOT NULL  DEFAULT 1,
    "frequency_hours" INT NOT NULL  DEFAULT 24,
    "total_sent" INT NOT NULL  DEFAULT 0,
    "total_clicks" INT NOT NULL  DEFAULT 0,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "is_active" INT NOT NULL  DEFAULT 1,
    "created_by_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "adclick";
        DROP TABLE IF EXISTS "advertisement";"""
