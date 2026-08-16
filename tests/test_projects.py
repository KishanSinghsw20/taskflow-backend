from app.core.security import create_access_token
from app.models.user import User


def create_test_user(db, email: str, name: str) -> User:
    user = User(email=email, name=name, password_hash="hashed")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_project_crud_and_authorization(client, db):
    # Setup two users
    user_a = create_test_user(db, "usera@example.com", "User A")
    user_b = create_test_user(db, "userb@example.com", "User B")

    token_a = create_access_token(user_a.id)
    token_b = create_access_token(user_b.id)

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. User A creates a project
    res = client.post(
        "/projects",
        json={"name": "User A Project", "description": "Private project"},
        headers=headers_a,
    )
    assert res.status_code == 201
    project_a = res.json()
    assert project_a["name"] == "User A Project"
    assert project_a["owner_id"] == user_a.id

    # 2. User A can list their project
    res = client.get("/projects", headers=headers_a)
    assert res.status_code == 200
    projects = res.json()
    assert len(projects) == 1
    assert projects[0]["id"] == project_a["id"]

    # 3. User B lists projects (should see 0 projects)
    res = client.get("/projects", headers=headers_b)
    assert res.status_code == 200
    assert len(res.json()) == 0

    # 4. User B tries to access User A's project (should return 404 Not Found)
    res = client.get(f"/projects/{project_a['id']}", headers=headers_b)
    assert res.status_code == 404

    # 5. User B tries to update User A's project (should return 404 Not Found)
    res = client.patch(
        f"/projects/{project_a['id']}",
        json={"name": "Hacked Name"},
        headers=headers_b,
    )
    assert res.status_code == 404

    # 6. User B tries to delete User A's project (should return 404 Not Found)
    res = client.delete(f"/projects/{project_a['id']}", headers=headers_b)
    assert res.status_code == 404

    # 7. User A updates their own project
    res = client.patch(
        f"/projects/{project_a['id']}",
        json={"name": "Updated Name"},
        headers=headers_a,
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Name"

    # 8. User A deletes their own project
    res = client.delete(f"/projects/{project_a['id']}", headers=headers_a)
    assert res.status_code == 204
