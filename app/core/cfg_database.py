from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.cfg_config import settings


def _engine(url: str, ssl_mode: str, pool_size: int, max_overflow: int):
    connect_args = {}
    if ssl_mode:
        connect_args["sslmode"] = ssl_mode
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        connect_args=connect_args,
    )


engine = _engine(
    settings.DATABASE_URL,
    ssl_mode=settings.DB_USE_SSL,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Conexion secundaria al nucleo bancario (bd_core_financiero) ---
# Usada solo por el servicio de promocion (sync_outbox -> core).
core_engine = _engine(
    settings.CORE_DATABASE_URL,
    ssl_mode=settings.CORE_DB_USE_SSL,
    pool_size=2,
    max_overflow=4,
)

SessionLocalCore = sessionmaker(autocommit=False, autoflush=False, bind=core_engine)