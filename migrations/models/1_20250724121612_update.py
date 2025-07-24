from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD "is_admin" INT NOT NULL  DEFAULT 0;
        ALTER TABLE "user" ADD "is_premium" INT NOT NULL  DEFAULT 0;
        ALTER TABLE "user" RENAME COLUMN "rating" TO "raiting";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" RENAME COLUMN "raiting" TO "rating";
        ALTER TABLE "user" DROP COLUMN "is_admin";
        ALTER TABLE "user" DROP COLUMN "is_premium";"""
