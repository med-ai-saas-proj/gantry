from gantry.db.factories import getAsyncEngine

from importlib.resources import files

from alembic import command as AlembicCmd
from alembic.config import Config
from pydantic_settings import (
    BaseSettings,
)


class Migrate(BaseSettings):
    async def cli_cmd(self):
        from gantry.db.factories import getSessionManager

        alembic_ini = files("gantry").joinpath("alembic.ini")
        alembic_cfg = Config(str(alembic_ini))

        def runMigrate(conn):
            alembic_cfg.attributes["connection"] = conn

            AlembicCmd.upgrade(alembic_cfg, "head")

        engine = getAsyncEngine()

        async with engine.begin() as conn:
            await conn.run_sync(runMigrate)
