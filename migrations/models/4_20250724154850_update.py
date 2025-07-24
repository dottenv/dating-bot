from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "ban" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "ban_type" VARCHAR(16) NOT NULL,
    "duration_hours" INT,
    "reason" TEXT,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "expires_at" TIMESTAMP,
    "is_active" INT NOT NULL  DEFAULT 1,
    "banned_by_id" INT REFERENCES "user" ("id") ON DELETE SET NULL,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "ban";"""
