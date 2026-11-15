import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import app, require_api_key
from src.models import KnowledgeArticle

TEST_ENGINE = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False)

@pytest.fixture()
def client():
    Base.metadata.create_all(bind=TEST_ENGINE)
    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_api_key] = lambda: None
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=TEST_ENGINE)

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_ticket_classification(client):
    response = client.post("/tickets", json={
        "customer_email": "customer@example.com",
        "subject": "API integration blocked",
        "message": "Urgent: API endpoint returns 401 and our integration is down."
    })
    assert response.status_code == 201
    data = response.json()
    assert data["category"] == "api_integration"
    assert data["priority"] == "high"

def test_assistant_retrieves_knowledge(client):
    db = TestingSession()
    db.add(KnowledgeArticle(title="Reset API token",
        content="Create a new API token, update your integration securely, test it, then revoke the old token.",
        tags="api token authentication"))
    db.commit()
    db.close()
    response = client.post("/assistant/ask", json={
        "question": "How do I reset an API token?", "conversation_id": "test-1"
    })
    assert response.status_code == 200
    result = response.json()
    assert result["sources"]
    assert result["generation_mode"] == "local_tfidf"
    assert "API token" in result["answer"]
