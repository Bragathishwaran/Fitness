"""Notification management and reminder tests."""

from datetime import date, timedelta

from app.services import notification_service
from tests.conftest import auth_headers, register_user
from tests.test_workouts import create_workout

TODAY = date.today()


def test_goal_notifications_and_read_flow(client):
    headers = auth_headers(register_user(client)["access_token"])
    goal = client.post(
        "/api/goals",
        json={
            "goal_type": "Steps",
            "target_value": 10000,
            "current_value": 0,
            "deadline": (TODAY + timedelta(days=10)).isoformat(),
        },
        headers=headers,
    ).json()

    client.patch(
        f"/api/goals/{goal['id']}/progress",
        json={"current_value": 8000},
        headers=headers,
    )
    listing = client.get("/api/notifications", headers=headers).json()
    assert listing["unread_count"] == 1
    assert listing["items"][0]["kind"] == "goal_progress"

    # The same threshold does not create duplicate alerts.
    client.patch(
        f"/api/goals/{goal['id']}/progress",
        json={"current_value": 8500},
        headers=headers,
    )
    assert client.get("/api/notifications", headers=headers).json()["unread_count"] == 1

    notification_id = listing["items"][0]["id"]
    read = client.post(
        f"/api/notifications/{notification_id}/read", headers=headers
    )
    assert read.status_code == 200
    assert read.json()["is_read"] is True
    assert client.get("/api/notifications/unread-count", headers=headers).json()[
        "unread_count"
    ] == 0

    client.patch(
        f"/api/goals/{goal['id']}/progress",
        json={"current_value": 10000},
        headers=headers,
    )
    completed = client.get("/api/notifications", headers=headers).json()
    assert completed["unread_count"] == 1
    assert completed["items"][0]["kind"] == "goal_completed"

    mark_all = client.post("/api/notifications/read-all", headers=headers)
    assert mark_all.status_code == 200
    assert mark_all.json()["updated"] == 1

    deleted = client.delete(
        f"/api/notifications/{completed['items'][0]['id']}", headers=headers
    )
    assert deleted.status_code == 204


def test_daily_reminders_are_not_duplicated(client, db):
    register_user(client)
    first = notification_service.generate_daily_reminders(db)
    second = notification_service.generate_daily_reminders(db)
    assert first == 1
    assert second == 0


def test_daily_reminders_skip_users_who_worked_out(client, db):
    headers = auth_headers(register_user(client)["access_token"])
    create_workout(client, headers)
    db.expire_all()
    assert notification_service.generate_daily_reminders(db) == 0


def test_notification_ownership(client):
    owner = auth_headers(register_user(client)["access_token"])
    other = auth_headers(
        register_user(client, email="other@example.com", username="Other")[
            "access_token"
        ]
    )
    goal = client.post(
        "/api/goals",
        json={
            "goal_type": "Steps",
            "target_value": 1000,
            "current_value": 800,
            "deadline": (TODAY + timedelta(days=10)).isoformat(),
        },
        headers=owner,
    ).json()
    notification_id = client.get("/api/notifications", headers=owner).json()["items"][0][
        "id"
    ]

    assert (
        client.post(
            f"/api/notifications/{notification_id}/read", headers=other
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/notifications/{notification_id}", headers=other
        ).status_code
        == 404
    )
    assert client.get("/api/notifications", headers=other).json()["total"] == 0
    assert goal["completion_percentage"] == 80
