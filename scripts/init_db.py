import os
from sqlalchemy import create_engine, Column, String, Text, Integer, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

# Use synchronous engine with SQLite
DB_URL = "sqlite:///./voice_agent.db"
engine = create_engine(DB_URL, echo=True)
Base = declarative_base()

# Define a simple model for testing
class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    content = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

def init_database():
    print("Creating database tables...")
    # Create the directory for SQLite DB if it doesn't exist
    if DB_URL.startswith("sqlite:///"):
        db_path = DB_URL.replace("sqlite:///", "")
        if db_path and not db_path.startswith(":"):
            os.makedirs(os.path.dirname(os.path.abspath(db_path)) or ".", exist_ok=True)
    
    # Create tables
    Base.metadata.create_all(engine)
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()
