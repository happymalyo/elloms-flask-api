from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from typing import Optional, List

from database.connection import get_async_db, create_tables
from database import crud
from schemas.user import User, UserCreate, UserLogin, Token
from schemas.conversation import Conversation, ConversationCreate, Message, MessageCreate
from schemas.crew import CrewJob, CrewJobCreate
from crews.crew_manager import kickoff_crew_with_context

# Initialize FastAPI
app = FastAPI(
    title="CrewAI Agent System with User Management",
    description="AI agent system with user authentication and conversation history",
    version="2.0.0"
)

# Security
security = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await crud.get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

# Startup event
@app.on_event("startup")
async def startup_event():
    await create_tables()

# Authentication endpoints
@app.post("/auth/register", response_model=User)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    # Check if user already exists
    db_user = await crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = await crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return await crud.create_user(db=db, user=user)

@app.post("/auth/login", response_model=Token)
async def login_user(user_login: UserLogin, db: AsyncSession = Depends(get_async_db)):
    user = await crud.authenticate_user(db, user_login.username, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# Conversation endpoints
@app.post("/conversations", response_model=Conversation)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    return await crud.create_conversation(db=db, user_id=current_user.id, conversation=conversation)

@app.get("/conversations", response_model=List[Conversation])
async def get_conversations(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    return await crud.get_user_conversations(db, user_id=current_user.id, skip=skip, limit=limit)

@app.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    conversation = await crud.get_conversation(db, conversation_id=conversation_id, user_id=current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@app.post("/conversations/{conversation_id}/messages", response_model=Message)
async def add_message(
    conversation_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # Verify conversation exists and belongs to user
    conversation = await crud.get_conversation(db, conversation_id=conversation_id, user_id=current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    message.conversation_id = conversation_id
    return await crud.create_message(db=db, message=message)

# CrewAI endpoints with conversation context
@app.post("/crew/kickoff-async")
async def kickoff_crew_async(
    job_data: CrewJobCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # Create crew job in database
    crew_job = await crud.create_crew_job(db=db, user_id=current_user.id, job_data=job_data)
    
    # Add user message to conversation if conversation_id provided
    if job_data.conversation_id:
        user_message = MessageCreate(
            conversation_id=job_data.conversation_id,
            role="user",
            content=f"Research and write about: {job_data.topic}",
            metadata={"job_id": crew_job.job_id}
        )
        await crud.create_message(db=db, message=user_message)
    
    # Start background task
    background_tasks.add_task(
        run_crew_background_with_db, 
        crew_job.job_id, 
        job_data.model_dump()
    )
    
    return {
        "job_id": crew_job.job_id,
        "status": "started",
        "message": "Crew workflow started in background"
    }

@app.get("/crew/jobs/{job_id}", response_model=CrewJob)
async def get_crew_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    job = await crud.get_crew_job(db, job_id=job_id, user_id=current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/crew/jobs", response_model=List[CrewJob])
async def get_user_jobs(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    return await crud.get_user_crew_jobs(db, user_id=current_user.id, skip=skip, limit=limit)

# Background task function
async def run_crew_background_with_db(job_id: str, inputs: dict):
    """Run crew task and update database"""
    from database.connection import AsyncSessionLocal
    from schemas.crew import CrewJobUpdate
    
    async with AsyncSessionLocal() as db:
        try:
            # Update job status to running
            await crud.update_crew_job(
                db, 
                job_id, 
                CrewJobUpdate(status="running")
            )
            
            # Get conversation context if available
            job = await crud.get_crew_job(db, job_id, None)  # Get job without user check for background task
            conversation_context = []
            
            if job and job.conversation_id:
                messages = await crud.get_conversation_messages(db, job.conversation_id, job.user_id)
                conversation_context = [
                    {"role": msg.role, "content": msg.content} 
                    for msg in messages[-10:]  # Last 10 messages for context
                ]
            
            # Execute crew with context
            result = kickoff_crew_with_context(inputs, conversation_context)
            
            # Update job with result
            await crud.update_crew_job(
                db,
                job_id,
                CrewJobUpdate(
                    status="completed",
                    result=str(result),
                    completed_at=datetime.utcnow()
                )
            )
            
            # Add assistant response to conversation
            if job and job.conversation_id:
                assistant_message = MessageCreate(
                    conversation_id=job.conversation_id,
                    role="assistant",
                    content=str(result),
                    metadata={"job_id": job_id, "type": "crew_result"}
                )
                await crud.create_message(db=db, message=assistant_message)
                
        except Exception as e:
            # Update job with error
            await crud.update_crew_job(
                db,
                job_id,
                CrewJobUpdate(
                    status="failed",
                    error_message=str(e),
                    completed_at=datetime.utcnow()
                )
            )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)