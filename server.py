from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_all, Column, String, Integer, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# --- DATABASE SETUP ---
# In production, you'd use an Environment Variable for this URL
DATABASE_URL = 'postgresql://neondb_owner:npg_iGZzB4ASW8TM@ep-nameless-boat-a1pw9sgp-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# We'll store the whole "state" as one JSON blob for simplicity, 
# or you could create separate tables for Assignments, Attendance, etc.
class UserData(Base):
    __tablename__ = "user_data"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    state = Column(JSON)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class StateUpdate(BaseModel):
    state: dict

@app.get("/load")
def load_data():
    db = SessionLocal()
    # For now, we just use one default user 'admin'
    user = db.query(UserData).filter(UserData.username == "admin").first()
    db.close()
    return user.state if user else {}

@app.post("/save")
def save_data(data: StateUpdate):
    db = SessionLocal()
    user = db.query(UserData).filter(UserData.username == "admin").first()
    
    if user:
        user.state = data.state
    else:
        user = UserData(username="admin", state=data.state)
        db.add(user)
    
    db.commit()
    db.close()
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    # Use 0.0.0.0 to allow external connections on Render
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)