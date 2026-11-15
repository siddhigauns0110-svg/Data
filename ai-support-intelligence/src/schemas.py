from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class TicketCreate(BaseModel):
    customer_email: EmailStr
    subject: str = Field(min_length=3, max_length=300)
    message: str = Field(min_length=5, max_length=10000)

class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_email: str
    subject: str
    message: str
    category: str
    priority: str
    sentiment: str
    escalated: bool
    status: str
    created_at: datetime

class ArticleCreate(BaseModel):
    title: str = Field(min_length=5, max_length=300)
    content: str = Field(min_length=20, max_length=20000)
    tags: list[str] = Field(default_factory=list)

class ArticleOut(BaseModel):
    id: int
    title: str
    content: str
    tags: list[str]

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=5000)
    conversation_id: str = Field(default="default", min_length=1, max_length=100)

class SourceOut(BaseModel):
    article_id: int
    title: str
    score: float

class AskResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[SourceOut]
    generation_mode: str
