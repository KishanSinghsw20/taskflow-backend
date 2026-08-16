from unittest.mock import patch
from app.core.security import create_access_token
from app.models.user import User


def create_test_user(db, email: str, name: str) -> User:
    user = User(email=email, name=name, password_hash="hashed")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_task_filtering_pagination_and_cache_invalidation(client, db):
    user = create_test_user(db, "cache_user@example.com", "Cache User")
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}

    # 1. Create project
    res_p = client.post("/projects", json={"name": "Cache Project"}, headers=headers)
    project_id = res_p.json()["id"]

    # 2. Create task
    res_t1 = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Task Original", "status": "todo"},
        headers=headers,
    )
    task_id = res_t1.json()["id"]

    # Mock redis_client get/setex/delete to explicitly verify cache behavior
    mock_storage = {}

    def mock_get(key):
        return mock_storage.get(key)

    def mock_setex(key, time, value):
        mock_storage[key] = value

    def mock_delete(*keys):
        for k in keys:
            mock_storage.pop(k, None)

    def mock_keys(pattern):
        # simple prefix match for test
        prefix = pattern.replace("*", "")
        return [k for k in mock_storage if k.startswith(prefix)]

    with patch("app.api.v1.tasks.redis_client.get", side_effect=mock_get), \
         patch("app.api.v1.tasks.redis_client.setex", side_effect=mock_setex), \
         patch("app.core.redis.redis_client.keys", side_effect=mock_keys), \
         patch("app.core.redis.redis_client.delete", side_effect=mock_delete):

        # First GET request: miss cache, populate cache
        res1 = client.get("/tasks?status=todo", headers=headers)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["total"] == 1
        assert data1["items"][0]["title"] == "Task Original"
        assert len(mock_storage) == 1  # Key cached in Redis

        # Second GET request: cache hit
        res2 = client.get("/tasks?status=todo", headers=headers)
        assert res2.status_code == 200
        assert res2.json()["items"][0]["title"] == "Task Original"

        # Task update: invalidates cache
        res_update = client.patch(
            f"/tasks/{task_id}",
            json={"title": "Task Updated", "status": "in_progress"},
            headers=headers,
        )
        assert res_update.status_code == 200
        assert len(mock_storage) == 0  # Cache invalidated!

        # Subsequent GET request: returns fresh updated data from DB
        res3 = client.get("/tasks?status=in_progress", headers=headers)
        assert res3.status_code == 200
        data3 = res3.json()
        assert data3["total"] == 1
        assert data3["items"][0]["title"] == "Task Updated"
