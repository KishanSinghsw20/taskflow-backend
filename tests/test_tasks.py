from app.core.security import create_access_token
from app.models.user import User


def create_test_user(db, email: str, name: str) -> User:
    user = User(email=email, name=name, password_hash="hashed")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_task_crud_and_authorization(client, db):
    user_a = create_test_user(db, "usera_task@example.com", "User A")
    user_b = create_test_user(db, "userb_task@example.com", "User B")

    headers_a = {"Authorization": f"Bearer {create_access_token(user_a.id)}"}
    headers_b = {"Authorization": f"Bearer {create_access_token(user_b.id)}"}

    # 1. User A creates a project
    res_p = client.post(
        "/projects",
        json={"name": "Project A"},
        headers=headers_a,
    )
    project_a_id = res_p.json()["id"]

    # 2. User A creates a task in Project A
    res_t = client.post(
        f"/projects/{project_a_id}/tasks",
        json={"title": "Task 1", "description": "Fix bug", "status": "todo"},
        headers=headers_a,
    )
    assert res_t.status_code == 201
    task_a = res_t.json()
    assert task_a["title"] == "Task 1"
    assert task_a["status"] == "todo"

    # 3. User B tries to create task in User A's project (should return 404)
    res_fail = client.post(
        f"/projects/{project_a_id}/tasks",
        json={"title": "Unauthorized Task"},
        headers=headers_b,
    )
    assert res_fail.status_code == 404

    # 4. User B tries to access User A's task (should return 404)
    res_get_fail = client.get(f"/tasks/{task_a['id']}", headers=headers_b)
    assert res_get_fail.status_code == 404

    # 5. User A updates task status to in_progress
    res_up = client.patch(
        f"/tasks/{task_a['id']}",
        json={"status": "in_progress"},
        headers=headers_a,
    )
    assert res_up.status_code == 200
    assert res_up.json()["status"] == "in_progress"

    # 6. User A deletes task
    res_del = client.delete(f"/tasks/{task_a['id']}", headers=headers_a)
    assert res_del.status_code == 204
