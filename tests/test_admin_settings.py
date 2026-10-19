def _admin_client(client):
    client.post("/auth/login", data={"email": "admin@uniguide.ug", "password": "admin123"})
    return client


def test_settings_page_lists_all_tabs(app, client):
    _admin_client(client)
    for tab in ("general", "account", "programmes", "recommendation",
                "dataset", "appearance", "logs"):
        response = client.get("/admin/settings?tab={0}".format(tab))
        assert response.status_code == 200, tab
    assert client.get("/admin/settings?tab=nonsense").status_code == 200


def test_settings_general_saves_and_validates(app, client):
    _admin_client(client)
    client.post("/admin/settings/general", data={
        "site_name": "UniGuide Uganda", "site_description": "Desc",
        "contact_email": "admin@uniguide.ug", "contact_phone": "+256 700 000 000",
        "homepage_image": "campus-hero.jfif", "items_per_page": "25",
        "date_format": "%Y-%m-%d",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert Setting.get("items_per_page") == "25"
        assert Setting.get("date_format") == "%Y-%m-%d"

    client.post("/admin/settings/general", data={
        "site_name": "", "items_per_page": "999",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert Setting.get("items_per_page") == "25"


def test_settings_programmes_saves_and_validates(app, client):
    _admin_client(client)
    client.post("/admin/settings/programmes", data={
        "default_admission_year": "2026/27",
        "preference_fields": "Computing,Engineering,Medicine",
        "active_default": "on",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert Setting.get("default_admission_year") == "2026/27"
        assert "Computing" in Setting.get("preference_fields")

    client.post("/admin/settings/programmes", data={
        "default_admission_year": "bad-format",
        "preference_fields": "Computing",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert Setting.get("default_admission_year") == "2026/27"

    client.post("/admin/settings/programmes", data={
        "default_admission_year": "2026/27",
        "preference_fields": "",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert "Computing" in Setting.get("preference_fields")


def test_settings_recommendation_saves_weights_and_toggles(app, client):
    _admin_client(client)
    client.post("/admin/settings/recommendation", data={
        "weight_essential": "4", "weight_relevant": "2", "weight_other": "1",
        "weight_subsidiary": "0.5", "budget_tolerance_pct": "40",
        "use_budget_match": "on", "use_region_match": "on",
        "use_career_match": "", "use_fee_preference": "",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert Setting.get("weight_essential") == "4.0"
        assert Setting.get("budget_tolerance_pct") == "40.0"
        assert Setting.get("use_budget_match") == "1"
        assert Setting.get("use_career_match") == "0"
        assert Setting.get("use_fee_preference") == "0"


def test_settings_recommendation_rejects_invalid_numbers(app, client):
    _admin_client(client)
    client.post("/admin/settings/recommendation", data={
        "weight_essential": "abc", "weight_relevant": "2", "weight_other": "1",
        "weight_subsidiary": "0.5", "budget_tolerance_pct": "40",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert Setting.get("weight_essential") != "abc"


def test_settings_recommendation_rejects_out_of_range(app, client):
    _admin_client(client)
    client.post("/admin/settings/recommendation", data={
        "weight_essential": "999", "weight_relevant": "2", "weight_other": "1",
        "weight_subsidiary": "0.5", "budget_tolerance_pct": "40",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert Setting.get("weight_essential") != "999.0"


def test_settings_recommendation_rejects_huge_tolerance(app, client):
    _admin_client(client)
    client.post("/admin/settings/recommendation", data={
        "weight_essential": "3", "weight_relevant": "2", "weight_other": "1",
        "weight_subsidiary": "0.5", "budget_tolerance_pct": "999",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert Setting.get("budget_tolerance_pct") != "999.0"


def test_settings_appearance_saves_theme_and_accent(app, client):
    _admin_client(client)
    client.post("/admin/settings/appearance", data={
        "theme": "dark", "accent_color": "#12345A", "show_logos": "on",
        "homepage_image": "campus-hero.jfif", "homepage_title": "Welcome",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert Setting.get("theme") == "dark"
        assert Setting.get("accent_color") == "#12345A"
        assert Setting.get("show_university_logos") == "1"

    client.post("/admin/settings/appearance", data={
        "theme": "neon", "accent_color": "red", "show_logos": "",
        "homepage_image": "campus-hero.jfif",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert Setting.get("theme") in ("light", "dark")
        assert Setting.get("accent_color").startswith("#")


def test_settings_appearance_rejects_path_traversal(app, client):
    _admin_client(client)
    client.post("/admin/settings/appearance", data={
        "theme": "light", "accent_color": "#12345A",
        "homepage_image": "../secret.png",
    }, follow_redirects=True)
    with app.app_context():
        from models import Setting

        assert Setting.get("homepage_image") != "../secret.png"


def test_settings_password_change_requires_current_password(app, client):
    _admin_client(client)
    client.post("/admin/settings/password", data={
        "current_password": "wrong", "new_password": "newpass123",
        "confirm_password": "newpass123",
    }, follow_redirects=True)
    with app.app_context():
        from models import User
        from werkzeug.security import check_password_hash

        admin = User.query.filter_by(role="admin").first()
        assert not check_password_hash(admin.password_hash, "newpass123")


def test_settings_password_change_rejects_weak_password(app, client):
    _admin_client(client)
    client.post("/admin/settings/password", data={
        "current_password": "admin123", "new_password": "short",
        "confirm_password": "short",
    }, follow_redirects=True)
    with app.app_context():
        from models import User
        from werkzeug.security import check_password_hash

        admin = User.query.filter_by(role="admin").first()
        assert check_password_hash(admin.password_hash, "admin123")


def test_settings_password_change_succeeds(app, client):
    _admin_client(client)
    response = client.post("/admin/settings/password", data={
        "current_password": "admin123", "new_password": "newpass123",
        "confirm_password": "newpass123",
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        from extensions import db
        from models import User
        from werkzeug.security import check_password_hash, generate_password_hash

        admin = User.query.filter_by(role="admin").first()
        assert check_password_hash(admin.password_hash, "newpass123")
        admin.password_hash = generate_password_hash("admin123")
        db.session.commit()


def test_settings_account_updates_profile(app, client):
    _admin_client(client)
    with app.app_context():
        from models import User

        admin = User.query.filter_by(role="admin").first()
        admin_id = admin.id
        admin_email = admin.email

    client.post("/admin/settings/account", data={
        "name": "Renamed Admin", "email": admin_email,
        "username": "adminrenamed",
    }, follow_redirects=True)
    with app.app_context():
        from models import User

        updated = User.query.get(admin_id)
        assert updated.name == "Renamed Admin"
        assert updated.email == admin_email


def test_settings_account_rejects_taken_email(app, client):
    _admin_client(client)
    with app.app_context():
        from models import User

        admin = User.query.filter_by(role="admin").first()
        student = User.query.filter_by(role="student").first()
        assert student is not None
        admin_id = admin.id

    client.post("/admin/settings/account", data={
        "name": "Admin", "email": student.email,
    }, follow_redirects=True)
    with app.app_context():
        from models import User

        assert User.query.get(admin_id).email != student.email


def test_admission_rules_remain_read_only_in_settings(app, client):
    response = _admin_client(client).get("/admin/settings?tab=recommendation")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "principal" in body.lower() or "admission" in body.lower()


def test_activity_logs_page_and_filters(app, client):
    _admin_client(client)
    assert client.get("/admin/logs").status_code == 200
    assert client.get("/admin/logs?action=login").status_code == 200
    assert client.get("/admin/logs?entity=university").status_code == 200


def test_login_writes_activity_log(app, client):
    client.post("/auth/login", data={"email": "admin@uniguide.ug", "password": "admin123"})
    with app.app_context():
        from models import ActivityLog

        assert ActivityLog.query.filter_by(action="login").count() >= 1


def test_settings_save_writes_activity_log(app, client):
    _admin_client(client)
    with app.app_context():
        from models import ActivityLog

        before = ActivityLog.query.filter_by(action="setting").count()
    client.post("/admin/settings/general", data={
        "site_name": "UniGuide Uganda", "items_per_page": "10",
        "date_format": "%d %B %Y",
    }, follow_redirects=True)
    with app.app_context():
        from models import ActivityLog

        assert ActivityLog.query.filter_by(action="setting").count() > before
