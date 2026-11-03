"""Analytics and dashboard tests."""

from datetime import date, timedelta

from tests.conftest import auth_headers, register_user
from tests.test_workouts import create_workout

TODAY = date.today()


def seed_workouts(client, headers):
    create_workout(
        client,
        headers,
        workout_name="Run",
        category="Cardio",
        duration=30,
        calories_burned=300,
    )
    create_workout(
        client,
        headers,
        workout_name="Lift",
        category="Strength",
        duration=60,
        calories_burned=400,
        workout_date=(TODAY - timedelta(days=1)).isoformat(),
    )
    create_workout(
        client,
        headers,
        workout_name="Flow",
        category="Yoga",
        duration=45,
        calories_burned=150,
        workout_date=(TODAY - timedelta(days=2)).isoformat(),
    )


def test_dashboard_uses_real_aggregated_data(client):
    headers = auth_headers(register_user(client)["access_token"])
    empty = client.get("/api/analytics/dashboard", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["stats"]["total_workouts"] == 0
    assert len(empty.json()["weekly_activity"]) == 7

    seed_workouts(client, headers)
    dashboard = client.get("/api/analytics/dashboard", headers=headers).json()
    assert dashboard["stats"]["total_workouts"] == 3
    assert dashboard["stats"]["total_calories"] == 850
    assert dashboard["stats"]["total_duration"] == 135
    assert dashboard["stats"]["current_streak"] == 3
    assert len(dashboard["recent_workouts"]) == 3

    distribution = dashboard["category_distribution"]
    assert len(distribution) == 3
    assert round(sum(item["percentage"] for item in distribution), 1) >= 99.5
    assert len(dashboard["weekly_activity"]) == 7


def test_analytics_overview_weekly_and_monthly(client):
    headers = auth_headers(register_user(client)["access_token"])
    seed_workouts(client, headers)

    overview = client.get(
        f"/api/analytics/overview?start_date={(TODAY - timedelta(days=6)).isoformat()}"
        f"&end_date={TODAY.isoformat()}",
        headers=headers,
    )
    assert overview.status_code == 200
    data = overview.json()
    assert data["totals"]["total_workouts"] == 3
    assert data["totals"]["average_duration"] == 45.0
    assert data["totals"]["active_days"] == 3
    assert len(data["daily_activity"]) == 7
    assert data["top_category"] == "Cardio"

    weekly = client.get(
        f"/api/analytics/weekly?start_date={(TODAY - timedelta(days=20)).isoformat()}"
        f"&end_date={TODAY.isoformat()}",
        headers=headers,
    )
    assert weekly.status_code == 200
    assert sum(week["workouts"] for week in weekly.json()) == 3

    monthly = client.get("/api/analytics/monthly?months=6", headers=headers)
    assert monthly.status_code == 200
    assert len(monthly.json()) == 6
    assert monthly.json()[-1]["workouts"] == 3

    categories = client.get("/api/analytics/categories", headers=headers)
    assert categories.status_code == 200
    assert len(categories.json()) == 3

    frequency = client.get("/api/analytics/frequency?days=7", headers=headers)
    assert frequency.status_code == 200
    assert frequency.json()["total_workouts"] == 3
    assert frequency.json()["current_streak"] == 3


def test_analytics_rejects_invalid_range(client):
    headers = auth_headers(register_user(client)["access_token"])
    response = client.get(
        f"/api/analytics/overview?start_date={TODAY.isoformat()}"
        f"&end_date={(TODAY - timedelta(days=3)).isoformat()}",
        headers=headers,
    )
    assert response.status_code == 400
