def test_admin_data_routes_admin_access(app, client):
    client.post("/auth/login", data={
        "email": "admin@uniguide.ug",
        "password": "admin123",
    }, follow_redirects=True)
    assert client.get("/admin/data").status_code == 200
    assert client.get("/admin/models").status_code == 200
    assert client.get("/admin/predict").status_code == 200


def test_admin_data_student_denied(registered_client):
    assert registered_client.get("/admin/data").status_code == 403
    assert registered_client.get("/admin/models").status_code == 403
    assert registered_client.get("/admin/predict").status_code == 403
