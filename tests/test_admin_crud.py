def _admin_client(client):
    client.post("/auth/login", data={"email": "admin@uniguide.ug", "password": "admin123"})
    return client


def test_university_create_and_edit(app, client):
    _admin_client(client)
    with app.app_context():
        from models import University

        before = University.query.count()

    response = client.post("/admin/universities/add", data={
        "name": "Test University of Uganda", "institution_type": "private",
        "region": "Northern", "district": "Gulu", "location": "Gulu City",
        "established": "2001", "website": "https://www.testuni.ug",
        "application_link": "https://apply.testuni.ug", "image": "",
        "active": "on",
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        from models import University

        created = University.query.filter_by(name="Test University of Uganda").first()
        assert created is not None
        assert created.district == "Gulu"
        assert University.query.count() == before + 1

        university_id = created.id

    response = client.post("/admin/universities/{0}/edit".format(university_id), data={
        "name": "Test University of Uganda", "institution_type": "private",
        "region": "Northern", "district": "Kampala", "location": "Gulu City",
        "established": "2001", "website": "https://www.testuni.ug",
        "application_link": "https://apply.testuni.ug", "image": "",
        "active": "on",
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        from models import University

        updated = University.query.get(university_id)
        assert updated.district == "Kampala"


def test_university_edit_rejects_invalid_url(app, client):
    _admin_client(client)
    with app.app_context():
        from models import University

        university = University.query.first()
        university_id = university.id
        original_website = university.website

    response = client.post("/admin/universities/{0}/edit".format(university_id), data={
        "name": university.name, "website": "not-a-url", "active": "on",
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        from models import University

        assert University.query.get(university_id).website == original_website


def test_university_toggle_activate_deactivate(app, client):
    _admin_client(client)
    with app.app_context():
        from models import University

        university = University.query.first()
        university_id = university.id
        original_active = university.active

    client.post("/admin/universities/{0}/toggle".format(university_id))
    with app.app_context():
        from models import University

        assert University.query.get(university_id).active is not original_active

    client.post("/admin/universities/{0}/toggle".format(university_id))
    with app.app_context():
        from models import University

        assert University.query.get(university_id).active is original_active


def test_university_delete_requires_confirmation(app, client):
    _admin_client(client)
    with app.app_context():
        from models import University

        university = University.query.first()
        university_id = university.id
        name = university.name

    client.post("/admin/universities/{0}/delete".format(university_id),
                data={"confirm_name": "wrong name"})
    with app.app_context():
        from models import University

        assert University.query.get(university_id) is not None

    client.post("/admin/universities/{0}/delete".format(university_id),
                data={"confirm_name": name}, follow_redirects=True)
    with app.app_context():
        from models import University

        assert University.query.get(university_id) is None


def test_programme_create_edit_toggle_delete(app, client):
    _admin_client(client)
    with app.app_context():
        from models import Programme, University

        university = University.query.first()
        before = Programme.query.count()

    response = client.post("/admin/programmes/add", data={
        "university_id": str(university.id), "name": "Bachelor of Testing",
        "level": "Bachelor", "qualification_level": "UACE",
        "duration_years": "3", "essential_subjects": "Mathematics",
        "principal_passes": "2", "cutoff_government": "8",
        "cutoff_private": "4", "tuition_private": "4000000",
        "admission_year": "2026/27", "official_source": "https://example.ug/src",
        "active": "on",
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        from models import Programme

        created = Programme.query.filter_by(name="Bachelor of Testing").first()
        assert created is not None
        assert Programme.query.count() == before + 1
        programme_id = created.id

    response = client.post("/admin/programmes/{0}/edit".format(programme_id), data={
        "university_id": str(university.id), "name": "Bachelor of Testing Renamed",
        "level": "Bachelor", "duration_years": "4",
        "admission_year": "2026/27", "active": "on",
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        from models import Programme

        assert Programme.query.get(programme_id).name == "Bachelor of Testing Renamed"
        assert Programme.query.get(programme_id).duration_years == 4

    response = client.post("/admin/programmes/{0}/edit".format(programme_id), data={
        "university_id": "0", "name": "", "admission_year": "26/27",
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        from models import Programme

        assert Programme.query.get(programme_id).name == "Bachelor of Testing Renamed"

    client.post("/admin/programmes/{0}/toggle".format(programme_id))
    with app.app_context():
        from models import Programme

        assert Programme.query.get(programme_id).active is False
    client.post("/admin/programmes/{0}/toggle".format(programme_id))

    client.post("/admin/programmes/{0}/delete".format(programme_id),
                data={"confirm_name": "wrong"}, follow_redirects=True)
    with app.app_context():
        from models import Programme

        assert Programme.query.get(programme_id) is not None

    client.post("/admin/programmes/{0}/delete".format(programme_id),
                data={"confirm_name": "Bachelor of Testing Renamed"}, follow_redirects=True)
    with app.app_context():
        from models import Programme

        assert Programme.query.get(programme_id) is None


def test_programme_detail_page(app, client):
    _admin_client(client)
    with app.app_context():
        from models import Programme

        programme_id = Programme.query.first().id
    response = client.get("/admin/programmes/{0}/view".format(programme_id))
    assert response.status_code == 200


def test_requirements_page_lists_programmes(app, client):
    _admin_client(client)
    response = client.get("/admin/requirements")
    assert response.status_code == 200
    response = client.get("/admin/requirements?incomplete=1")
    assert response.status_code == 200


def test_career_create_rename_delete(app, client):
    _admin_client(client)
    with app.app_context():
        from models import Career

        before = Career.query.count()

    client.post("/admin/careers/add", data={"name": "Career Under Test",
                                            "description": "temp"},
                follow_redirects=True)
    with app.app_context():
        from models import Career

        career = Career.query.filter_by(name="Career Under Test").first()
        assert career is not None
        assert Career.query.count() == before + 1
        career_id = career.id

    client.post("/admin/careers/{0}/edit".format(career_id),
                data={"name": "Career Renamed"}, follow_redirects=True)
    with app.app_context():
        from models import Career

        assert Career.query.get(career_id).name == "Career Renamed"

    client.post("/admin/careers/{0}/delete".format(career_id),
                data={"confirm_name": "wrong"}, follow_redirects=True)
    with app.app_context():
        from models import Career

        assert Career.query.get(career_id) is not None

    client.post("/admin/careers/{0}/delete".format(career_id),
                data={"confirm_name": "Career Renamed"}, follow_redirects=True)
    with app.app_context():
        from models import Career

        assert Career.query.get(career_id) is None


def test_user_edit_preserves_role_and_updates_name(app, client):
    _admin_client(client)
    with app.app_context():
        from models import User

        student = User.query.filter_by(role="student").first()
        student_id = student.id
        assert student.role == "student"

    client.post("/admin/users/{0}/edit".format(student_id), data={
        "name": "Renamed Student", "email": student.email, "role": "student",
        "active": "on",
    }, follow_redirects=True)
    with app.app_context():
        from models import User

        updated = User.query.get(student_id)
        assert updated.name == "Renamed Student"
        assert updated.role == "student"


def test_last_admin_cannot_be_deleted_or_deactivated(app, client):
    _admin_client(client)
    with app.app_context():
        from models import User

        admin = User.query.filter_by(role="admin").first()
        admin_id = admin.id
        admin_name = admin.name

    client.post("/admin/users/{0}/delete".format(admin_id),
                data={"confirm_name": admin_name}, follow_redirects=True)
    with app.app_context():
        from models import User

        assert User.query.get(admin_id) is not None

    client.post("/admin/users/{0}/toggle".format(admin_id), follow_redirects=True)
    with app.app_context():
        from models import User

        assert User.query.get(admin_id).active is not False


def test_self_delete_blocked(app, client):
    _admin_client(client)
    with app.app_context():
        from models import User

        admin = User.query.filter_by(role="admin").first()
        admin_id = admin.id

    client.post("/admin/users/{0}/delete".format(admin_id),
                data={"confirm_name": "anything"}, follow_redirects=True)
    with app.app_context():
        from models import User

        assert User.query.get(admin_id) is not None


def test_user_delete_cascades_related_records(app, client):
    _admin_client(client)
    with app.app_context():
        from extensions import db
        from models import (ComparisonHistory, Notification, PredictionLog,
                            SavedRecommendation, StudentProfile, User)

        user = User(name="Cascade User", email="cascade@x.ug",
                    password_hash="x", role="student", active=True)
        db.session.add(user)
        db.session.commit()
        db.session.add(StudentProfile(user_id=user.id, preferred_region="Central"))
        db.session.add(SavedRecommendation(user_id=user.id, programme_id=1,
                                          status="saved", suitability=80))
        db.session.add(ComparisonHistory(user_id=user.id, university_ids="[1]",
                                         programme_ids="[1]"))
        db.session.add(Notification(user_id=user.id, message="hello", link="/dashboard"))
        db.session.add(PredictionLog(user_id=user.id, kind="programme",
                                     input_summary="in", output_summary="out"))
        db.session.commit()
        user_id = user.id

    client.post("/admin/users/{0}/delete".format(user_id),
                data={"confirm_name": "Cascade User"}, follow_redirects=True)
    with app.app_context():
        from models import (ComparisonHistory, Notification, PredictionLog,
                            SavedRecommendation, StudentProfile, User)

        assert User.query.get(user_id) is None
        assert StudentProfile.query.filter_by(user_id=user_id).count() == 0
        assert SavedRecommendation.query.filter_by(user_id=user_id).count() == 0
        assert ComparisonHistory.query.filter_by(user_id=user_id).count() == 0
        assert Notification.query.filter_by(user_id=user_id).count() == 0
        assert PredictionLog.query.filter_by(user_id=user_id).count() == 0


def test_enquiry_toggle_and_delete(app, client):
    _admin_client(client)
    with app.app_context():
        from extensions import db
        from models import Enquiry

        enquiry = Enquiry(name="Tester", email="t@x.ug", message="hello there")
        db.session.add(enquiry)
        db.session.commit()
        enquiry_id = enquiry.id

    client.post("/admin/enquiries/{0}/toggle".format(enquiry_id))
    with app.app_context():
        from models import Enquiry

        assert Enquiry.query.get(enquiry_id).read is True

    client.post("/admin/enquiries/{0}/delete".format(enquiry_id),
                data={"confirm_name": "Tester"}, follow_redirects=True)
    with app.app_context():
        from models import Enquiry

        assert Enquiry.query.get(enquiry_id) is None


def test_users_page_search_and_filter(app, client):
    _admin_client(client)
    assert client.get("/admin/users").status_code == 200
    assert client.get("/admin/users?role=admin").status_code == 200
    assert client.get("/admin/users?q=admin").status_code == 200


def test_universities_and_programmes_search(app, client):
    _admin_client(client)
    assert client.get("/admin/universities?q=maker&status=active&sort=region&dir=asc").status_code == 200
    assert client.get("/admin/programmes?q=bus&level=Bachelor&status=active").status_code == 200
    assert client.get("/admin/programmes?university=1").status_code == 200


def test_dashboard_shows_key_counts(app, client):
    _admin_client(client)
    response = client.get("/admin/")
    assert response.status_code == 200


def test_export_csv_streams_download(app, client):
    _admin_client(client)
    for entity in ("universities", "programmes", "careers"):
        response = client.get("/admin/export/{0}".format(entity))
        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith("text/csv")


def test_import_run_is_non_destructive(app, client):
    _admin_client(client)
    with app.app_context():
        from models import Career, Programme, University

        before = (University.query.count(), Programme.query.count(), Career.query.count())

    response = client.post("/admin/import/run", follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        from models import Career, Programme, University

        after = (University.query.count(), Programme.query.count(), Career.query.count())
        assert after[0] >= before[0]
        assert after[1] >= before[1]
        assert after[2] >= before[2]


def test_data_pages_and_activity_logs(app, client):
    _admin_client(client)
    assert client.get("/admin/data").status_code == 200
    assert client.get("/admin/logs").status_code == 200
    assert client.get("/admin/logs?action=update&entity=programme").status_code == 200


def test_student_denied_on_all_new_admin_routes(registered_client):
    routes = [
        "/admin/universities", "/admin/universities/add",
        "/admin/programmes", "/admin/programmes/add",
        "/admin/requirements", "/admin/careers", "/admin/careers/add",
        "/admin/users", "/admin/enquiries", "/admin/settings",
        "/admin/logs", "/admin/data", "/admin/export/programmes",
        "/admin/export/universities", "/admin/export/careers",
    ]
    for route in routes:
        assert registered_client.get(route).status_code == 403, route
