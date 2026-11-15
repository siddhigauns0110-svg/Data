from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import settings
from .database import Base, engine, get_db
from .intelligence import classify_ticket, generate_answer, retrieve_articles
from .models import ConversationMessage, KnowledgeArticle, Ticket
from .schemas import ArticleCreate, ArticleOut, AskRequest, AskResponse, TicketCreate, TicketOut

app = FastAPI(title=settings.app_name, version="0.1.0",
              description="Support triage, knowledge retrieval, and grounded answer drafting.")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        if db.query(KnowledgeArticle).count() == 0:
            db.add_all([
                KnowledgeArticle(title="Rotating an API token", tags="api token authentication security",
                    content="Create a replacement token in developer settings before revoking the old one. Store it in a server-side secret manager, update the integration, and verify successful requests. Never commit tokens to source control. After verification, revoke the old token and monitor authentication errors."),
                KnowledgeArticle(title="Troubleshooting HTTP 401 and 403", tags="api authentication unauthorized forbidden",
                    content="For HTTP 401, verify the Authorization header, token validity, and authentication scheme. For HTTP 403, check token scopes and account permissions. Confirm the correct environment and review logs without sharing secrets."),
                KnowledgeArticle(title="Checking a delayed delivery", tags="delivery shipment tracking parcel delay",
                    content="Use the shipment tracking reference to check the latest scan and estimated delivery. If there is no update beyond the normal service window, raise a ticket with the tracking reference, destination postal code, and last known event."),
            ])
            db.commit()
    finally:
        db.close()

def require_api_key(x_api_key: str | None = Header(default=None)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="A valid X-API-Key header is required.")

def db_session(db: Session = Depends(get_db)):
    yield db

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}

@app.post("/tickets", response_model=TicketOut, status_code=201, dependencies=[Depends(require_api_key)])
def create_ticket(payload: TicketCreate, db: Session = Depends(db_session)):
    ticket = Ticket(customer_email=str(payload.customer_email), subject=payload.subject,
                    message=payload.message, **classify_ticket(payload.subject, payload.message))
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket

@app.get("/tickets/{ticket_id}", response_model=TicketOut, dependencies=[Depends(require_api_key)])
def get_ticket(ticket_id: int, db: Session = Depends(db_session)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return ticket

@app.get("/analytics/overview", dependencies=[Depends(require_api_key)])
def analytics_overview(db: Session = Depends(db_session)):
    total = db.query(func.count(Ticket.id)).scalar() or 0
    priorities = dict(db.query(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority).all())
    categories = dict(db.query(Ticket.category, func.count(Ticket.id)).group_by(Ticket.category).all())
    escalated = db.query(func.count(Ticket.id)).filter(Ticket.escalated.is_(True)).scalar() or 0
    return {"total_tickets": total, "escalated_tickets": escalated,
            "by_priority": priorities, "by_category": categories}

@app.post("/knowledge-base/articles", response_model=ArticleOut, status_code=201,
          dependencies=[Depends(require_api_key)])
def create_article(payload: ArticleCreate, db: Session = Depends(db_session)):
    if db.query(KnowledgeArticle).filter(KnowledgeArticle.title == payload.title).first():
        raise HTTPException(status_code=409, detail="An article with this title already exists.")
    article = KnowledgeArticle(title=payload.title, content=payload.content, tags=", ".join(payload.tags))
    db.add(article)
    db.commit()
    db.refresh(article)
    return {"id": article.id, "title": article.title, "content": article.content, "tags": payload.tags}

@app.get("/knowledge-base/articles", response_model=list[ArticleOut],
         dependencies=[Depends(require_api_key)])
def list_articles(db: Session = Depends(db_session)):
    articles = db.query(KnowledgeArticle).order_by(KnowledgeArticle.id).all()
    return [{"id": a.id, "title": a.title, "content": a.content,
             "tags": [tag.strip() for tag in a.tags.split(",") if tag.strip()]} for a in articles]

@app.post("/assistant/ask", response_model=AskResponse, dependencies=[Depends(require_api_key)])
def ask_assistant(payload: AskRequest, db: Session = Depends(db_session)):
    articles = db.query(KnowledgeArticle).all()
    matches = retrieve_articles(payload.question, articles)
    answer, mode = generate_answer(payload.question, matches, settings.openai_api_key, settings.openai_model)
    db.add_all([
        ConversationMessage(conversation_id=payload.conversation_id, role="user", content=payload.question),
        ConversationMessage(conversation_id=payload.conversation_id, role="assistant", content=answer),
    ])
    db.commit()
    return {"conversation_id": payload.conversation_id, "answer": answer,
            "sources": [{"article_id": a.id, "title": a.title, "score": round(score, 4)} for a, score in matches],
            "generation_mode": mode}
