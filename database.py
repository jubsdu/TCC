from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///ultrapulse.db"

engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False}
)

Base = declarative_base()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

db_session = SessionLocal()


def init_db():
    import models
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Banco de dados inicializado com sucesso!")