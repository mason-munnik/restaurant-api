def test_create_restaurant_returns_200(client):
    response = client.post(
        "/restaurants",
        json={"name": "Trattoria Roma", "cuisine": "Italian", "location": "Downtown"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Trattoria Roma"
    assert body["cuisine"] == "Italian"
    assert body["location"] == "Downtown"
    assert "id" in body


def test_create_restaurant_name_only_returns_200(client):
    response = client.post("/restaurants", json={"name": "No Frills Diner"})
    assert response.status_code == 200
    body = response.json()
    assert body["cuisine"] is None
    assert body["location"] is None


def test_create_restaurant_empty_name_rejected(client):
    response = client.post("/restaurants", json={"name": ""})
    assert response.status_code == 422


def test_create_restaurant_whitespace_name_rejected(client):
    response = client.post("/restaurants", json={"name": "   "})
    assert response.status_code == 422


def test_create_restaurant_missing_key_returns_401(make_client):
    anonymous_client = make_client(api_key=None)
    response = anonymous_client.post("/restaurants", json={"name": "No Frills Diner"})
    assert response.status_code == 401


def test_create_restaurant_wrong_key_returns_403(make_client):
    wrong_key_client = make_client(api_key="wrong-key")
    response = wrong_key_client.post("/restaurants", json={"name": "No Frills Diner"})
    assert response.status_code == 403


def test_list_restaurants_is_public(make_client):
    anonymous_client = make_client(api_key=None)
    assert anonymous_client.get("/restaurants").status_code == 200


def test_list_restaurants_limit_caps_returned_rows(client):
    for i in range(3):
        client.post("/restaurants", json={"name": f"Restaurant {i}"})

    response = client.get("/restaurants?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_restaurants_offset_skips_rows(client):
    existing_count = len(client.get("/restaurants?limit=100").json())
    created = [
        client.post("/restaurants", json={"name": f"Restaurant {i}"}).json()
        for i in range(3)
    ]

    response = client.get(f"/restaurants?offset={existing_count + 1}&limit=10")
    assert response.status_code == 200
    returned_ids = [r["id"] for r in response.json()]
    assert created[0]["id"] not in returned_ids
    assert created[1]["id"] in returned_ids
    assert created[2]["id"] in returned_ids


def test_get_restaurant_by_id_returns_200(client):
    created = client.post("/restaurants", json={"name": "Trattoria Roma"}).json()

    response = client.get(f"/restaurants/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Trattoria Roma"


def test_get_restaurant_by_id_returns_404_when_missing(client):
    assert client.get("/restaurants/999999").status_code == 404


def test_delete_restaurant_with_no_reviews_returns_200(client):
    created = client.post("/restaurants", json={"name": "Trattoria Roma"}).json()

    response = client.delete(f"/restaurants/{created['id']}")
    assert response.status_code == 200
    assert client.get(f"/restaurants/{created['id']}").status_code == 404


def test_delete_restaurant_missing_returns_404(client):
    assert client.delete("/restaurants/999999").status_code == 404


def test_delete_restaurant_missing_key_returns_401(make_client):
    client = make_client()
    created = client.post("/restaurants", json={"name": "Trattoria Roma"}).json()

    anonymous_client = make_client(api_key=None)
    response = anonymous_client.delete(f"/restaurants/{created['id']}")
    assert response.status_code == 401


def test_delete_restaurant_wrong_key_returns_403(make_client):
    client = make_client()
    created = client.post("/restaurants", json={"name": "Trattoria Roma"}).json()

    wrong_key_client = make_client(api_key="wrong-key")
    response = wrong_key_client.delete(f"/restaurants/{created['id']}")
    assert response.status_code == 403


def test_delete_restaurant_with_reviews_returns_409(client):
    created = client.post("/restaurants", json={"name": "Trattoria Roma"}).json()
    client.post(
        "/analyze",
        json={"restaurant_id": created["id"], "review_text": "food was great"},
    )

    response = client.delete(f"/restaurants/{created['id']}")
    assert response.status_code == 409
    # restaurant must survive an attempted-but-blocked delete
    assert client.get(f"/restaurants/{created['id']}").status_code == 200
