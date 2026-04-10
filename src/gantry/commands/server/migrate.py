from alembic import command as AlembicCmd
from gantry.db.factories import getAsyncEngine

from pathlib import Path

from alembic.config import Config
from pydantic_settings import (
    BaseSettings,
)


class Migrate(BaseSettings):
    async def cli_cmd(self):
        from gantry.settings import AppSettings
        from gantry.db.factories import getSessionManager

        PACKAGE_DIR = Path(__file__).parents[4]
        alembic_cfg = Config(PACKAGE_DIR / "alembic.ini")

        def runMigrate(conn):
            alembic_cfg.attributes["connection"] = conn

            AlembicCmd.upgrade(alembic_cfg, "head")

        engine = getAsyncEngine()

        async with engine.begin() as conn:
            await conn.run_sync(runMigrate)
