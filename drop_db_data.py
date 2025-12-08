import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure DATABASE_URL is set
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

# Import Base and models
from app.db import Base # Assuming Base is defined in app.db
from app import models # Import your models so Base.metadata knows about them

def drop_all_tables():
    print(f"Connecting to database: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    
    print("Attempting to drop all tables...")
    try:
        # This will drop all tables registered with Base.metadata
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped successfully.")
    except Exception as e:
        print(f"An error occurred while dropping tables: {e}")
        print("Please ensure the database is accessible and the user has sufficient permissions.")

if __name__ == "__main__":
    drop_all_tables()
