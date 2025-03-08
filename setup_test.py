import os
import sys
import importlib
import shutil
from pathlib import Path

def ensure_directory(directory):
    Path(directory).mkdir(parents=True, exist_ok=True)
    print(f"✓ Directory created: {directory}")

def create_env_file():
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("# Required API keys\n")
            f.write("VAPI_API_KEY=your-vapi-api-key\n")
            f.write("ANTHROPIC_API_KEY=your-anthropic-api-key\n")
            f.write("\n# Application settings\n")
            f.write("APP_ENV=development\n")
            f.write("APP_DEBUG=true\n")
            f.write("DATABASE_URL=sqlite:///./voice_agent.db\n")
        print("✓ Created .env file (please edit with your API keys)")
    else:
        print("✓ .env file already exists")

def setup_prompts_directory():
    prompts_dir = "./prompts"
    ensure_directory(prompts_dir)
    
    # Check for prompt files in current directory
    prompt_files = [f for f in os.listdir() if f.endswith(".txt") and "_" in f]
    
    if prompt_files:
        for file in prompt_files:
            shutil.copy(file, os.path.join(prompts_dir, file))
            print(f"✓ Copied {file} to prompts directory")
    else:
        print("⚠ No prompt template files found in current directory")
        print("  Please copy your prompt templates to the 'prompts' directory")

def setup_database():
    # Use synchronous SQLAlchemy
    from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, Integer, Boolean, DateTime
    from sqlalchemy.ext.declarative import declarative_base
    import datetime
    
    # Create engine
    DB_URL = "sqlite:///./voice_agent.db"
    engine = create_engine(DB_URL, echo=True)
    
    # Create base
    Base = declarative_base()
    
    # Define PromptTemplate model
    class PromptTemplate(Base):
        __tablename__ = "prompt_templates"
        id = Column(String(36), primary_key=True)
        name = Column(String(100), nullable=False, unique=True)
        content = Column(Text, nullable=False)
        version = Column(Integer, default=1)
        is_active = Column(Boolean, default=True)
        created_at = Column(DateTime, default=datetime.datetime.now)
    
    # Create tables
    Base.metadata.create_all(engine)
    print("✓ Database initialized")
    
    # Check if database file was created
    if os.path.exists("voice_agent.db"):
        print("✓ SQLite database file created")
    else:
        print("⚠ SQLite database file not created")

def check_imports():
    required_packages = [
        "fastapi", "sqlalchemy", "pydantic", "httpx", 
        "python-dotenv", "uvicorn"
    ]
    
    missing = []
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing.append(package)
    
    if not missing:
        print("✓ All required packages installed")
    else:
        print(f"⚠ Missing packages: {', '.join(missing)}")
        print("  Run: pip install " + " ".join(missing))

def main():
    print("==== Voice Agent Setup Test ====\n")
    
    # Check directory structure
    ensure_directory("app")
    ensure_directory("app/db")
    ensure_directory("app/core")
    
    # Create .env file
    create_env_file()
    
    # Setup prompts directory
    setup_prompts_directory()
    
    # Check required packages
    check_imports()
    
    # Initialize database
    try:
        setup_database()
    except Exception as e:
        print(f"⚠ Database setup error: {e}")
    
    print("\n==== Next Steps ====")
    print("1. Edit the .env file with your actual API keys")
    print("2. Make sure your prompt templates are in the 'prompts' directory")
    print("3. Set up N8N with a webhook for VAPI")
    print("4. Test the full flow with a call to your VAPI number")

if __name__ == "__main__":
    main()
