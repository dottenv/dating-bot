from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "premiumpurchase" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "stars_amount" INT NOT NULL,
    "duration_days" INT NOT NULL,
    "telegram_payment_id" VARCHAR(256),
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "premiumpurchase";"""
