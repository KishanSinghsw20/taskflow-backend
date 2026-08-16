from datetime import datetime, timedelta, timezone
from app.core.security import create_access_token
from app.models.user import User
from app.tasks.notifications import check_overdue_tasks, send_task_reassignment_notification


def create_test_user(db, email: str, name: str) -> User:
    user = User(email=email, name=name, password_hash="hashed")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_reassignment_and_overdue_notifications(client, db):
    user_a = create_test_user(db, "notify_owner@example.com", "Owner User")
    user_b = create_test_user(db, "notify_assignee@example.com", "Assignee User")

    headers_a = {"Authorization": f"Bearer {create_access_token(user_a.id)}"}
    headers_b = {"Authorization": f"Bearer {create_access_token(user_b.id)}"}

    # 1. User A creates project
    res_p = client.post("/projects", json={"name": "Notify Project"}, headers=headers_a)
    project_id = res_p.json()["id"]

    # 2. User A creates task assigned to User B
    res_t = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Important Task", "assignee_id": user_b.id},
        headers=headers_a,
    )
    task_id = res_t.json()["id"]

    # Trigger background worker task directly for test with test db session
    send_task_reassignment_notification(task_id, user_b.id, "Important Task", db=db)

    # 3. User B checks notifications
    res_n = client.get("/notifications", headers=headers_b)
    assert res_n.status_code == 200
    notifications_b = res_n.json()
    assert len(notifications_b) == 1
    assert notifications_b[0]["type"] == "reassignment"
    assert notifications_b[0]["is_read"] is False

    # Mark notification as read
    n_id = notifications_b[0]["id"]
    res_read = client.patch(f"/notifications/{n_id}/read", headers=headers_b)
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True

    # 4. Overdue Task Detection & Duplicate Prevention Test
    # Set task due_date to yesterday
    res_due = client.patch(
        f"/tasks/{task_id}",
        json={"due_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()},
        headers=headers_a,
    )
    assert res_due.status_code == 200

    # Execute periodic task check twice
    check_overdue_tasks(db=db)
    check_overdue_tasks(db=db)  # Second call should NOT duplicate unread overdue notification

    res_overdue = client.get("/notifications", headers=headers_b)
    overdue_notifs = [n for n in res_overdue.json() if n["type"] == "overdue"]
    assert len(overdue_notifs) == 1  # Exactly 1 overdue notification created (no duplicate)

