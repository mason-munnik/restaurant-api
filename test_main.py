import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from database import Base


def _make_stub_pipeline(label="POSITIVE", score=0.95):
    def stub_pipeline(text, **kwargs):
        return [{"label": label, "score": score}]
    return stub_pipeline


@pytest.fixture
def client():
    # isolated in-memory DB per test, so tests never touch the real reviews.db
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db
    main.analyzer._pipeline = _make_stub_pipeline()

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()


def test_analyze_valid_review_returns_200(client):
    response = client.post(
        "/analyze",
        json={"restaurant_id": 1, "review_text": "The food was fantastic!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 0.95
    assert body["verdict"] == "Positive"


def test_analyze_review_text_empty_rejected(client):
    response = client.post(
        "/analyze",
        json={"restaurant_id": 1, "review_text": ""},
    )
    assert response.status_code == 422


def test_analyze_review_text_whitespace_only_rejected(client):
    response = client.post(
        "/analyze",
        json={"restaurant_id": 1, "review_text": "   "},
    )
    assert response.status_code == 422


def test_analyze_review_text_too_short_rejected(client):
    response = client.post(
        "/analyze",
        json={"restaurant_id": 1, "review_text": "too short"},
    )
    assert response.status_code == 422


def test_analyze_review_text_exactly_three_words_accepted(client):
    response = client.post(
        "/analyze",
        json={"restaurant_id": 1, "review_text": "food was great"},
    )
    assert response.status_code == 200


def test_analyze_restaurant_id_at_boundary_accepted(client):
    response = client.post(
        "/analyze",
        json={"restaurant_id": 10000, "review_text": "food was great"},
    )
    assert response.status_code == 200


def test_analyze_restaurant_id_over_boundary_rejected(client):
    response = client.post(
        "/analyze",
        json={"restaurant_id": 10001, "review_text": "food was great"},
    )
    assert response.status_code == 422


def test_delete_existing_review_returns_200_and_removes_it(client):
    create_response = client.post(
        "/analyze",
        json={"restaurant_id": 1, "review_text": "food was great"},
    )
    review_id = create_response.json()["id"]

    delete_response = client.delete(f"/reviews/{review_id}")
    assert delete_response.status_code == 200

    reviews = client.get("/reviews").json()
    assert all(r["id"] != review_id for r in reviews)


def test_delete_nonexistent_review_returns_404(client):
    response = client.delete("/reviews/999999")
    assert response.status_code == 404
