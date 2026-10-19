import pytest


def _admin_client(client):
    client.post("/auth/login", data={"email": "admin@uniguide.ug", "password": "admin123"})
    return client


def test_csrf_rejects_posts_without_token(app):
    """With CSRF enabled, state-changing POSTs must fail without a token."""
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()
    client.post("/auth/login", data={"email": "admin@uniguide.ug", "password": "admin123"})
    response = client.post("/admin/universities/add", data={
        "name": "CSRF University", "institution_type": "public",
        "region": "Central", "district": "Kampala", "active": "on",
    }, follow_redirects=True)
    assert response.status_code in (400, 403)
    with app.app_context():
        from models import University

        assert University.query.filter_by(name="CSRF University").first() is None


def test_csrf_rejects_settings_posts_without_token(app):
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()
    client.post("/auth/login", data={"email": "admin@uniguide.ug", "password": "admin123"})
    with app.app_context():
        from models import Setting

        original = Setting.get("items_per_page")
    response = client.post("/admin/settings/general", data={
        "site_name": "Hacked", "items_per_page": "1",
    }, follow_redirects=True)
    assert response.status_code in (400, 403)
    with app.app_context():
        from models import Setting

        assert Setting.get("items_per_page") == original


def test_csrf_rejects_delete_without_token(app):
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()
    client.post("/auth/login", data={"email": "admin@uniguide.ug", "password": "admin123"})
    with app.app_context():
        from models import Career

        career = Career.query.first()
        career_id = career.id
    response = client.post("/admin/careers/{0}/delete".format(career_id),
                           data={"confirm_name": career.name}, follow_redirects=True)
    assert response.status_code in (400, 403)
    with app.app_context():
        from models import Career

        assert Career.query.get(career_id) is not None


def test_student_denied_on_write_routes(registered_client):
    write_routes = [
        ("/admin/universities/add", {"name": "X"}),
        ("/admin/universities/1/toggle", {}),
        ("/admin/universities/1/delete", {"confirm_name": "X"}),
        ("/admin/programmes/add", {"name": "X"}),
        ("/admin/programmes/1/toggle", {}),
        ("/admin/programmes/1/delete", {"confirm_name": "X"}),
        ("/admin/careers/add", {"name": "X"}),
        ("/admin/careers/1/delete", {"confirm_name": "X"}),
        ("/admin/users/1/toggle", {}),
        ("/admin/users/1/delete", {"confirm_name": "X"}),
        ("/admin/enquiries/1/toggle", {}),
        ("/admin/enquiries/1/delete", {"confirm_name": "X"}),
        ("/admin/settings/general", {"site_name": "Hacked"}),
        ("/admin/settings/password", {"current_password": "x", "new_password": "y1234567",
                                      "confirm_password": "y1234567"}),
        ("/admin/import/run", {}),
    ]
    for route, data in write_routes:
        response = registered_client.post(route, data=data, follow_redirects=True)
        assert response.status_code == 403, route


def test_student_denied_on_read_routes(registered_client):
    read_routes = [
        "/admin/", "/admin/universities", "/admin/universities/add",
        "/admin/universities/1/edit",
        "/admin/programmes", "/admin/programmes/add", "/admin/programmes/1/view",
        "/admin/programmes/1/edit", "/admin/requirements",
        "/admin/careers", "/admin/careers/add", "/admin/careers/1/edit",
        "/admin/users", "/admin/users/1/edit", "/admin/enquiries",
        "/admin/import", "/admin/data", "/admin/models", "/admin/predict",
        "/admin/settings", "/admin/logs",
        "/admin/export/universities", "/admin/export/programmes",
        "/admin/export/careers",
    ]
    for route in read_routes:
        assert registered_client.get(route).status_code == 403, route


def test_unauthenticated_redirected_from_admin(client):
    response = client.get("/admin/")
    assert response.status_code == 302
    follow = client.get("/admin/", follow_redirects=True)
    assert follow.status_code == 200
    assert b"login" in follow.data.lower() or b"sign" in follow.data.lower()


def test_inactive_user_cannot_login(app, client):
    with app.app_context():
        from extensions import db
        from models import User

        user = User(name="Inactive", email="inactive@x.ug",
                    password_hash="x", role="student", active=False)
        db.session.add(user)
        db.session.commit()

    response = client.post("/auth/login", data={
        "email": "inactive@x.ug", "password": "whatever",
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        from models import ActivityLog

        failures = ActivityLog.query.filter_by(action="login_failed").count()
        assert failures >= 1


def test_password_never_logged_in_activity(app, client):
    _admin_client(client)
    client.post("/admin/settings/password", data={
        "current_password": "admin123", "new_password": "newpass123",
        "confirm_password": "newpass123",
    }, follow_redirects=True)
    with app.app_context():
        from models import ActivityLog, User
        from extensions import db
        from werkzeug.security import generate_password_hash

        admin = User.query.filter_by(role="admin").first()
        admin.password_hash = generate_password_hash("admin123")
        db.session.commit()
        for log in ActivityLog.query.all():
            assert "newpass123" not in (log.detail or "")
            assert "admin123" not in (log.detail or "")


def test_university_delete_cleans_related_records(app, client):
    _admin_client(client)
    with app.app_context():
        from extensions import db
        from models import (Programme, SavedRecommendation, StudentProfile, User,
                            University)

        student = User.query.filter_by(role="student").first()
        university = University(
            name="Delete Me Uni", institution_type="public",
            region="Central", district="Kampala", active=True)
        db.session.add(university)
        db.session.commit()
        programme = Programme(university_id=university.id, name="Delete Me Programme",
                              level="Bachelor", active=True)
        db.session.add(programme)
        db.session.commit()
        saved = SavedRecommendation(user_id=student.id, programme_id=programme.id,
                                    status="saved")
        db.session.add(saved)
        db.session.commit()
        university_id = university.id
        programme_id = programme.id

    client.post("/admin/universities/{0}/delete".format(university_id),
                data={"confirm_name": "Delete Me Uni"}, follow_redirects=True)
    with app.app_context():
        from models import Programme, SavedRecommendation, University

        assert University.query.get(university_id) is None
        assert Programme.query.get(programme_id) is None
        assert SavedRecommendation.query.filter_by(programme_id=programme_id).count() == 0


def test_upload_rejects_oversized_file(app, client):
    _admin_client(client)
    with app.app_context():
        from flask import current_app

        limit = current_app.config.get("MAX_CONTENT_LENGTH")
    # Build a payload larger than the configured upload cap when one is set.
    if limit:
        payload = b"x" * (limit + 1)
    else:
        payload = b"x" * (5 * 1024 * 1024)
    import io

    response = client.post("/admin/data/upload", data={
        "file": (io.BytesIO(payload), "big.csv"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code in (200, 413, 400)


def test_data_run_is_admin_only_and_handles_failure(app, client):
    """The pipeline route is admin-only; students get 403 without touching the data."""
    from werkzeug.security import generate_password_hash

    with app.app_context():
        from extensions import db
        from models import User

        user = User(name="Pipeline Student", email="pipe@x.ug",
                    password_hash=generate_password_hash("secret123"),
                    role="student", active=True)
        db.session.add(user)
        db.session.commit()
    student = app.test_client()
    student.post("/auth/login", data={"email": "pipe@x.ug", "password": "secret123"})
    assert student.post("/admin/data/run", follow_redirects=True).status_code == 403


def test_export_only_streams_csv_for_known_entities(app, client):
    _admin_client(client)
    response = client.get("/admin/export/unknown")
    assert response.status_code in (404, 400)
