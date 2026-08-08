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


# --- request param validation -------------------------------------------------

PAYLOAD = {"restaurant_id": 1, "review_text": "food was great"}


def test_reviews_limit_default_returns_200(client):
    assert client.get("/reviews").status_code == 200


def test_reviews_limit_one_accepted(client):
    assert client.get("/reviews?limit=1").status_code == 200


def test_reviews_limit_hundred_accepted(client):
    assert client.get("/reviews?limit=100").status_code == 200


def test_reviews_limit_zero_rejected(client):
    response = client.get("/reviews?limit=0")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "limit"]


def test_reviews_limit_over_max_rejected(client):
    assert client.get("/reviews?limit=101").status_code == 422


def test_reviews_limit_negative_rejected(client):
    assert client.get("/reviews?limit=-1").status_code == 422


def test_reviews_limit_non_integer_rejected(client):
    assert client.get("/reviews?limit=abc").status_code == 422


def test_reviews_limit_caps_returned_rows(client):
    # the only test proving `limit` is actually applied, not merely validated
    for _ in range(3):
        client.post("/analyze", json=PAYLOAD)

    response = client.get("/reviews?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_delete_review_id_one_reaches_handler(client):
    # the ge=1 boundary passes validation and reaches the handler
    assert client.delete("/reviews/1").status_code == 404


def test_delete_review_id_zero_rejected(client):
    response = client.delete("/reviews/0")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "review_id"]


def test_delete_review_id_negative_rejected(client):
    assert client.delete("/reviews/-1").status_code == 422


def test_delete_review_id_non_integer_rejected(client):
    assert client.delete("/reviews/abc").status_code == 422
