# File: backend/main.py

import os
import uvicorn
import re
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth
from typing import Dict, Any, Optional

# Import the components from our modular files
from .agents.core_agent import agent_executor
from .database_connector import Base, engine, get_db
from .models import User, Query, FineTuningData, SQLFeedback
from .agents.agent_memory import get_chat_history, add_to_chat_history

# Load environment variables
load_dotenv()

# --- Firebase Admin SDK Setup ---
# Initialize the Firebase Admin SDK using a mock credentials object.
# In a real-world app, you would use a service account key.
mock_firebase_config = {
    "type": "service_account",
    "project_id": "mock-project",
    "private_key_id": "mock_key_id",
    "private_key": "---BEGIN PRIVATE KEY---...---END PRIVATE KEY---\n",
    "client_email": "firebase-adminsdk-mock@mock-project.iam.gserviceaccount.com",
    "client_id": "1234567890",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-mock%40mock-project.iam.gserviceaccount.com"
}
try:
    cred = credentials.Certificate(mock_firebase_config)
    firebase_admin.initialize_app(cred)
except ValueError:
    pass

# Initialize FastAPI app
app = FastAPI(
    title="Conversational Agent Backend",
    description="A FastAPI backend for a multi-purpose conversational agent."
)

# Configure CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create all database tables on startup.
@app.on_event("startup")
def create_db_tables():
    Base.metadata.create_all(bind=engine)

# User authentication middleware to verify token on all protected endpoints
async def get_current_user_id(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid."
        )
    
    id_token = auth_header.split(" ")[1]
    
    try:
        # Verify the ID token. In a production app, this connects to Google's servers.
        # For this mock environment, we'll simulate a valid token.
        if id_token.startswith("mock-token-"):
            user_id = id_token.replace("mock-token-", "")
            return user_id
        
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token['uid']
    except Exception as e:
        print(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials."
        )

# Pydantic models for request bodies
class UserCredentials(BaseModel):
    username: str
    password: str

@app.get("/")
def read_root():
    return {"message": "Conversational Agent Backend is online!"}

@app.post("/signup")
async def signup(credentials: UserCredentials, db: Session = Depends(get_db)):
    # This is a mock signup. In a real app, you would use Firebase Auth's SDK.
    # We generate a mock user ID and create a custom token.
    user = db.query(User).filter_by(username=credentials.username).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists."
        )
    
    new_user_id = os.urandom(16).hex()
    new_user = User(id=new_user_id, username=credentials.username)
    db.add(new_user)
    db.commit()
    
    # Generate a custom token (mocked for this environment)
    custom_token = f"mock-token-{new_user_id}"
    return {"token": custom_token, "userId": new_user_id}

@app.post("/login")
async def login(credentials: UserCredentials, db: Session = Depends(get_db)):
    # Mock login logic. In a real app, you'd verify credentials here.
    user = db.query(User).filter_by(username=credentials.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )
    
    # Generate a custom token (mocked for this environment)
    custom_token = f"mock-token-{user.id}"
    return {"token": custom_token, "userId": user.id}

def detect_language(text: str) -> str:
    """
    A simple language detection function.
    In a production environment, you would use a dedicated library like `langdetect`.
    """
    bangla_chars_pattern = re.compile(r'[\u0980-\u09FF]')
    banglish_keywords = ["ki obosstha", "kemon achen", "kothai jaben"]
    text_lower = text.lower()
    
    if bangla_chars_pattern.search(text):
        return "bangla"
    if any(keyword in text_lower for keyword in banglish_keywords):
        return "banglish"
    
    return "english"

@app.post("/chat")
async def chat(request: Request, user_input: Dict[str, Any], db: Session = Depends(get_db)):
    query = user_input.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    # Get user ID from the authentication dependency
    user_id = await get_current_user_id(request)

    try:
        current_chat_history = get_chat_history()
        
        # Invoke the agent to get a response and the full state.
        result = agent_executor.invoke(
            {
                "user_id": user_id,
                "input": query,
                "chat_history": current_chat_history,
                "db": db # Pass the database session to the agent
            }
        )
        
        response_text = result.get("response", "An error occurred with the agent's response.")
        
        # Add the conversation to chat history.
        add_to_chat_history(user_input=query, ai_response=response_text)

        # Record the main interaction.
        new_query = Query(
            user_id=user_id,
            query_text=query,
            response_text=response_text
        )
        db.add(new_query)
        
        # Record data for general fine-tuning.
        llm_intent = result.get("intent")
        identified_language = detect_language(query)
        new_fine_tuning_data = FineTuningData(
            user_query=query,
            llm_intent=llm_intent,
            identified_language=identified_language,
            generated_response=response_text
        )
        db.add(new_fine_tuning_data)
        
        # Record data for SQL fine-tuning if applicable.
        generated_sql = result.get("sql_query")
        if generated_sql:
            # Assume SQL is correct for now, but a feedback mechanism could update this.
            is_correct = result.get("validation_status") == "valid"
            new_sql_feedback = SQLFeedback(
                user_id=user_id,
                user_query=query,
                generated_sql=generated_sql,
                is_correct=is_correct
            )
            db.add(new_sql_feedback)
            
        db.commit()
        
        return {"response": response_text}

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
