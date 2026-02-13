from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# --- DATABASE SETUP ---
# Fetching the URL from Render's Environment Variables
# If not found, it defaults to a local sqlite for safety, but in production, 
# Render will provide the Neon URL.
DATABASE_URL = os.environ.get("DATABASE_URL")

# Fix for SQLAlchemy: Neon/Heroku strings often start with 'postgres://'
# but SQLAlchemy requires 'postgresql://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    print("WARNING: No DATABASE_URL found. Falling back to local SQLite.")
    DATABASE_URL = "sqlite:///./local_test.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DATABASE MODEL ---
class UserData(Base):
    __tablename__ = "user_data"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    state = Column(JSON)

# This replaces the incorrect 'from sqlalchemy import create_all'
# It creates the tables in Neon if they don't exist
Base.metadata.create_all(bind=engine)

# --- APP SETUP ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class StateUpdate(BaseModel):
    state: dict

# --- ENDPOINTS ---

@app.get("/")
def health_check():
    return {"status": "online", "message": "Student OS API is running"}

@app.get("/load")
def load_data():
    db = SessionLocal()
    try:
        user = db.query(UserData).filter(UserData.username == "admin").first()
        return user.state if user else {}
    finally:
        db.close()

@app.post("/save")
def save_data(data: StateUpdate):
    db = SessionLocal()
    try:
        user = db.query(UserData).filter(UserData.username == "admin").first()
        if user:
            user.state = data.state
        else:
            user = UserData(username="admin", state=data.state)
            db.add(user)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    # Render provides a $PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
