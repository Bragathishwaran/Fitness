"""Fitness goal tests."""

from datetime import date, timedelta

from tests.conftest import auth_headers, register_user

TODAY = date.today()


def create_goal(client, headers, **overrides):
    payload = {
        "goal_type": "Steps",
        "target_value": 100000,
        "current_value": 0,
        "deadline": (TODAY + timedelta(days=30)).isoformat(),
    }
    payload.update(overrides)
    response = client.post("/api/goals", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_goal_lifecycle_and_percentages(client):
    headers = auth_headers(register_user(client)["access_token"])
    goal = create_goal(client, headers)
    assert goal["status"] == "active"
    assert goal["completion_percentage"] == 0

    progress = client.patch(
        f"/api/goals/{goal['id']}/progress",
        json={"current_value": 50000},
        headers=headers,
    )
    assert progress.status_code == 200
    assert progress.json()["completion_percentage"] == 50
    assert progress.json()["status"] == "active"

    edited = client.put(
        f"/api/goals/{goal['id']}",
        json={"target_value": 60000, "goal_type": "Muscle Gain"},
        headers=headers,
    )
    assert edited.status_code == 200
    assert edited.json()["completion_percentage"] == 83.33

    completed = client.patch(
        f"/api/goals/{goal['id']}/progress",
        json={"current_value": 60000},
        headers=headers,
    )
    assert completed.json()["status"] == "completed"
    assert completed.json()["completion_percentage"] == 100

    listing = client.get("/api/goals", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["completed"] == 1

    deleted = client.delete(f"/api/goals/{goal['id']}", headers=headers)
    assert deleted.status_code == 204


def test_overdue_goal_detection(client):
    headers = auth_headers(register_user(client)["access_token"])
    goal = create_goal(
        client,
        headers,
        deadline=(TODAY - timedelta(days=1)).isoformat(),
        current_value=100,
    )
    assert goal["status"] == "overdue"
    assert client.get("/api/goals", headers=headers).json()["overdue"] == 1


def test_goal_ownership_and_validation(client):
    owner = auth_headers(register_user(client)["access_token"])
    other = auth_headers(
        register_user(client, email="other@example.com", username="Other")[
            "access_token"
        ]
    )
    goal = create_goal(client, owner)

    assert client.get(f"/api/goals/{goal['id']}", headers=other).status_code == 404
    assert (
        client.patch(
            f"/api/goals/{goal['id']}/progress",
            json={"current_value": 10},
            headers=other,
        ).status_code
        == 404
    )
    assert client.get("/api/goals", headers=other).json()["total"] == 0

    invalid = client.post(
        "/api/goals",
        json={
            "goal_type": "Steps",
            "target_value": 0,
            "current_value": 0,
            "deadline": (TODAY + timedelta(days=5)).isoformat(),
        },
        headers=owner,
    )
    assert invalid.status_code == 422
