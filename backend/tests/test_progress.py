"""Daily progress aggregation tests."""

from datetime import date, timedelta

from tests.conftest import auth_headers, register_user
from tests.test_workouts import create_workout


def test_daily_progress_and_history(client):
    headers = auth_headers(register_user(client)["access_token"])
    today = date.today()
    yesterday = today - timedelta(days=1)

    create_workout(client, headers, workout_name="Run", duration=30, calories_burned=300)
    create_workout(
        client,
        headers,
        workout_name="Weights",
        category="Strength",
        duration=45,
        calories_burned=250,
    )
    create_workout(
        client,
        headers,
        workout_name="Yoga",
        category="Yoga",
        duration=20,
        calories_burned=80,
        workout_date=yesterday.isoformat(),
    )

    daily = client.get(
        f"/api/progress/daily?date={today.isoformat()}", headers=headers
    )
    assert daily.status_code == 200
    body = daily.json()
    assert body["total_workouts"] == 2
    assert body["total_calories"] == 550
    assert body["total_duration"] == 75
    assert len(body["workouts"]) == 2

    empty = client.get(
        f"/api/progress/daily?date={(today - timedelta(days=5)).isoformat()}",
        headers=headers,
    )
    assert empty.json()["total_workouts"] == 0

    history = client.get(
        f"/api/progress/history?start_date={yesterday.isoformat()}&end_date={today.isoformat()}",
        headers=headers,
    )
    assert history.status_code == 200
    data = history.json()
    assert data["total_workouts"] == 3
    assert data["total_calories"] == 630
    assert data["total_duration"] == 95
    assert len(data["days"]) == 2


def test_progress_resyncs_when_workout_moves_days(client):
    headers = auth_headers(register_user(client)["access_token"])
    today = date.today()
    yesterday = today - timedelta(days=1)
    workout = create_workout(client, headers, workout_date=today.isoformat())

    moved = client.put(
        f"/api/workouts/{workout['id']}",
        json={"workout_date": yesterday.isoformat()},
        headers=headers,
    )
    assert moved.status_code == 200

    today_progress = client.get(
        f"/api/progress/daily?date={today.isoformat()}", headers=headers
    ).json()
    yesterday_progress = client.get(
        f"/api/progress/daily?date={yesterday.isoformat()}", headers=headers
    ).json()
    assert today_progress["total_workouts"] == 0
    assert yesterday_progress["total_workouts"] == 1

    client.delete(f"/api/workouts/{workout['id']}", headers=headers)
    after_delete = client.get(
        f"/api/progress/daily?date={yesterday.isoformat()}", headers=headers
    ).json()
    assert after_delete["total_workouts"] == 0


def test_invalid_progress_range(client):
    headers = auth_headers(register_user(client)["access_token"])
    today = date.today()
    response = client.get(
        f"/api/progress/history?start_date={today.isoformat()}&end_date={(today - timedelta(days=2)).isoformat()}",
        headers=headers,
    )
    assert response.status_code == 400
