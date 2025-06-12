from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CrewJobBase(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500)
    additional_context: Optional[str] = (None,)
    prompt: Optional[str] = (None,)
    platform: Optional[str] = None


class CrewJobCreate(CrewJobBase):
    conversation_id: Optional[int] = None


class CrewJobUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class CrewJob(CrewJobBase):
    id: int
    job_id: str
    user_id: int
    conversation_id: Optional[int] = None
    status: str
    result: Optional[str] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
