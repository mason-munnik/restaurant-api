def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_requires_no_api_key(make_client):
    anonymous_client = make_client(api_key=None)
    assert anonymous_client.get("/health").status_code == 200
