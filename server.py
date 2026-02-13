from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

# --- DATABASE SETUP ---
DATABASE_URL = os.environ.get("DATABASE_URL")

# Fix for SQLAlchemy with Neon/Heroku
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    print("WARNING: No DATABASE_URL found. Falling back to local SQLite.")
    DATABASE_URL = "sqlite:///./studentos.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DATABASE MODEL ---
class UserData(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    usn = Column(String, unique=True, index=True)  # Unique ID for the student
    username = Column(String)
    state = Column(JSON)

# Create tables
Base.metadata.create_all(bind=engine)

# --- APP SETUP ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class UserLogin(BaseModel):
    usn: str
    username: str

class StateUpdate(BaseModel):
    usn: str
    username: str
    state: dict

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ENDPOINTS ---

@app.get("/")
def health_check():
    return {"status": "online", "message": "Student OS API is running"}

@app.post("/login")
def login_and_load(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Tries to load data for the USN. 
    If user doesn't exist, returns empty state (frontend handles default).
    """
    user = db.query(UserData).filter(UserData.usn == user_data.usn).first()
    
    if user:
        # Update username if it changed, just in case
        if user.username != user_data.username:
            user.username = user_data.username
            db.commit()
        return {"found": True, "state": user.state, "username": user.username}
    else:
        return {"found": False, "state": None}

@app.post("/save")
def save_data(data: StateUpdate, db: Session = Depends(get_db)):
    """
    Saves or creates the user data based on USN.
    """
    try:
        user = db.query(UserData).filter(UserData.usn == data.usn).first()
        
        if user:
            user.state = data.state
            user.username = data.username # Update name if changed
        else:
            # Create new user
            user = UserData(usn=data.usn, username=data.username, state=data.state)
            db.add(user)
            
        db.commit()
        return {"status": "success", "usn": data.usn}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
