import asyncio
import sys

from sqlalchemy import text

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from src.database.session import _get_engine


async def stamp_if_needed():
    engine = _get_engine()
    async with engine.begin() as conn:
        # Check if users table exists (meaning DB was initialized via create_all)
        result = await conn.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');"
            )
        )
        is_initialized = result.scalar()

        # Check if alembic_version exists
        result2 = await conn.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version');"
            )
        )
        has_alembic = result2.scalar()

        if is_initialized and not has_alembic:
            print("Stamping database with initial migration (8d95be3632af)...")
            await conn.execute(
                text(
                    "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO alembic_version (version_num) VALUES ('8d95be3632af');"
                )
            )
        elif not is_initialized:
            print("Database is completely empty. Alembic will run all migrations.")
        else:
            print("Database is already tracked by Alembic.")


if __name__ == "__main__":
    asyncio.run(stamp_if_needed())
