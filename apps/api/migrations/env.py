import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure src/ directory is available on sys.path
CURRENT_DIR = Path(__file__).resolve().parent
API_DIR = CURRENT_DIR.parent
SRC_DIR = API_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from strata.core.config import settings
from strata.db.base import Base

# Import all domain models to ensure they are registered on Base.metadata
import strata.domain.materials.models  # noqa: F401
import strata.domain.qualification.models  # noqa: F401
import strata.domain.marketplace.models  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata provides autogenerate support
target_metadata = Base.metadata


def get_url() -> str:
    """Retrieves authoritative database URL from Alembic config or STRATA application settings."""
    cfg_url = config.get_main_option("sqlalchemy.url")
    if cfg_url and not cfg_url.startswith("driver://"):
        return cfg_url
    return settings.effective_database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Connects to configured database (Supabase PostgreSQL or local SQLite) and executes migrations.
    """
    url = get_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        connect_args["connect_timeout"] = settings.DATABASE_CONNECT_TIMEOUT
        if ("supabase.co" in url or "pooler.supabase.com" in url) and "sslmode" not in url:
            connect_args["sslmode"] = "require"

    from sqlalchemy import create_engine
    connectable = create_engine(
        url,
        connect_args=connect_args,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=url.startswith("sqlite"),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
