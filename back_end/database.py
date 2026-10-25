"""Configuração do SQLite e do SQLAlchemy para o VitaPulse."""
from __future__ import annotations

import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    # O aplicativo segue funcionando sem .env; variáveis podem ser definidas no terminal.
    pass

_default_db = (BASE_DIR / "ultrapulse.db").as_posix()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_default_db}")

_connect_args = {"check_same_thread": False, "timeout": 30} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=_connect_args)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

Base = declarative_base()
SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
SessionLocal = scoped_session(SessionFactory)


def init_db() -> None:
    """Cria as tabelas e adiciona colunas novas em bancos de versões anteriores."""
    import models  # noqa: F401 - registra todos os modelos no metadata
    Base.metadata.create_all(bind=engine)

    if DATABASE_URL.startswith("sqlite"):
        with engine.begin() as connection:
            columns = {
                row[1]
                for row in connection.exec_driver_sql("PRAGMA table_info(users)").fetchall()
            }
            # Usuários já existentes devem conseguir entrar sem refazer o onboarding.
            if "onboarding_reason" not in columns:
                connection.exec_driver_sql("ALTER TABLE users ADD COLUMN onboarding_reason VARCHAR(40)")
            if "onboarding_completed" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN NOT NULL DEFAULT 1"
                )


if __name__ == "__main__":
    init_db()
    print(f"SQLite inicializado em: {_default_db}")
