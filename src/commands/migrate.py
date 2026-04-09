from alembic import command

from alembic.config import Config


def runMigrate(cli_args: list[str]):
    alembic_cfg = Config("alembic.ini")
    print(alembic_cfg)
    # command.upgrade(alembic_cfg, "head")
