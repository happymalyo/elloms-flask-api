from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid
from datetime import datetime
from passlib.context import CryptContext

from .models import User, Conversation, Message, CrewJob
from schemas.user import UserCreate, UserUpdate
from schemas.conversation import ConversationCreate, MessageCreate
from schemas.crew import CrewJobCreate, CrewJobUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User CRUD
async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user: UserCreate) -> User:
    hashed_password = pwd_context.hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    user = await get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# Conversation CRUD
async def create_conversation(db: AsyncSession, user_id: int, conversation: ConversationCreate) -> Conversation:
    db_conversation = Conversation(
        user_id=user_id,
        title=conversation.title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    db.add(db_conversation)
    await db.commit()
    await db.refresh(db_conversation)
    return db_conversation

async def get_user_conversations(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 50) -> List[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_conversation(db: AsyncSession, conversation_id: int, user_id: int) -> Optional[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .options(selectinload(Conversation.messages))
    )
    return result.scalar_one_or_none()

# Message CRUD
async def create_message(db: AsyncSession, message: MessageCreate) -> Message:
    db_message = Message(**message.model_dump())
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    
    # Update conversation timestamp
    await db.execute(
        update(Conversation)
        .where(Conversation.id == message.conversation_id)
        .values(updated_at=datetime.now())
    )
    await db.commit()
    
    return db_message

async def get_conversation_messages(db: AsyncSession, conversation_id: int, user_id: int) -> List[Message]:
    # First verify user owns the conversation
    conversation = await get_conversation(db, conversation_id, user_id)
    if not conversation:
        return []
    
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return result.scalars().all()

# CrewJob CRUD
async def create_crew_job(db: AsyncSession, user_id: int, job_data: CrewJobCreate) -> CrewJob:
    job_id = str(uuid.uuid4())
    db_job = CrewJob(
        job_id=job_id,
        user_id=user_id,
        conversation_id=job_data.conversation_id,
        topic=job_data.topic,
        additional_context=job_data.additional_context,
        status="pending"
    )
    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)
    return db_job

async def update_crew_job(db: AsyncSession, job_id: str, job_update: CrewJobUpdate) -> Optional[CrewJob]:
    result = await db.execute(select(CrewJob).where(CrewJob.job_id == job_id))
    db_job = result.scalar_one_or_none()
    
    if db_job:
        update_data = job_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_job, field, value)
        
        await db.commit()
        await db.refresh(db_job)
    
    return db_job

async def get_crew_job(db: AsyncSession, job_id: str, user_id: int) -> Optional[CrewJob]:
    result = await db.execute(
        select(CrewJob)
        .where(CrewJob.job_id == job_id, CrewJob.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def get_user_crew_jobs(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 50) -> List[CrewJob]:
    result = await db.execute(
        select(CrewJob)
        .where(CrewJob.user_id == user_id)
        .order_by(CrewJob.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()