from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.user import Base

# Initialize SQLite database
engine = create_engine('sqlite:///fashion_advisor.db')

def init_db():
    Base.metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
