"""Workout CRUD and ownership tests."""

from datetime import date, timedelta

from tests.conftest import auth_headers, register_user

TODAY = date.today().isoformat()


def create_workout(client, headers, **overrides):
    """Create a workout with sensible defaults."""
    payload = {
        "workout_name": "Morning Run",
        "category": "Cardio",
        "duration": 30,
        "calories_burned": 300,
        "workout_date": TODAY,
    }
    payload.update(overrides)
    response = client.post("/api/workouts", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_workout_crud_and_filters(client):
    token = register_user(client)["access_token"]
    headers = auth_headers(token)
    created = create_workout(client, headers)
    assert created["category"] == "Cardio"
    assert created["user_id"] > 0

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    create_workout(
        client,
        headers,
        workout_name="Evening Yoga",
        category="Yoga",
        duration=45,
        calories_burned=150,
        workout_date=yesterday,
    )

    all_workouts = client.get("/api/workouts", headers=headers)
    assert all_workouts.status_code == 200
    assert all_workouts.json()["total"] == 2

    cardio = client.get("/api/workouts?category=Cardio", headers=headers)
    assert cardio.json()["total"] == 1

    search = client.get("/api/workouts?search=yoga", headers=headers)
    assert search.json()["total"] == 1

    dated = client.get(f"/api/workouts?start_date={TODAY}&end_date={TODAY}", headers=headers)
    assert dated.json()["total"] == 1

    single = client.get(f"/api/workouts/{created['id']}", headers=headers)
    assert single.status_code == 200
    assert single.json()["workout_name"] == "Morning Run"

    updated = client.put(
        f"/api/workouts/{created['id']}",
        json={"workout_name": "Long Run", "duration": 60, "calories_burned": 600},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["duration"] == 60

    deleted = client.delete(f"/api/workouts/{created['id']}", headers=headers)
    assert deleted.status_code == 204

    missing = client.get(f"/api/workouts/{created['id']}", headers=headers)
    assert missing.status_code == 404


def test_workout_validation(client):
    headers = auth_headers(register_user(client)["access_token"])

    bad_category = client.post(
        "/api/workouts",
        json={
            "workout_name": "Dance",
            "category": "Dance",
            "duration": 30,
            "calories_burned": 100,
            "workout_date": TODAY,
        },
        headers=headers,
    )
    assert bad_category.status_code == 422

    bad_duration = client.post(
        "/api/workouts",
        json={
            "workout_name": "Dance",
            "category": "Cardio",
            "duration": 0,
            "calories_burned": 100,
            "workout_date": TODAY,
        },
        headers=headers,
    )
    assert bad_duration.status_code == 422


def test_users_cannot_access_each_others_workouts(client):
    owner = register_user(client)["access_token"]
    other = register_user(
        client, email="other@example.com", username="Other"
    )["access_token"]

    workout = create_workout(client, auth_headers(owner))
    other_headers = auth_headers(other)

    assert client.get(
        f"/api/workouts/{workout['id']}", headers=other_headers
    ).status_code == 404
    assert client.put(
        f"/api/workouts/{workout['id']}",
        json={"duration": 10},
        headers=other_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/workouts/{workout['id']}", headers=other_headers
    ).status_code == 404
    assert client.get("/api/workouts", headers=other_headers).json()["total"] == 0
