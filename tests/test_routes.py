def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"UniGuide" in response.data


def test_register_flow(client):
    response = client.get("/auth/register")
    assert response.status_code == 200
    response = client.post("/auth/register", data={
        "name": "Aisha Nakato",
        "email": "aisha@student.ug",
        "password": "secret123",
        "confirm": "secret123",
    }, follow_redirects=False)
    assert response.status_code == 302


def test_login_flow(app, client):
    client.post("/auth/register", data={
        "name": "Aisha Nakato",
        "email": "aisha@student.ug",
        "password": "secret123",
        "confirm": "secret123",
    })
    response = client.post("/auth/login", data={
        "email": "aisha@student.ug",
        "password": "secret123",
    }, follow_redirects=True)
    assert response.status_code == 200


def test_profile_requires_login(client):
    response = client.get("/profile")
    assert response.status_code == 302


def test_ugandan_profile_submission(registered_client):
    data = {
        "citizenship": "ugandan",
        "uce_summary": "Six credits",
        "subject_1": "Biology", "grade_1": "A",
        "subject_2": "Chemistry", "grade_2": "B",
        "subject_3": "Mathematics", "grade_3": "B",
        "subsidiary_gp": "A",
        "preferred_field": "Computing & IT",
        "budget": "6000000",
        "preferred_region": "Central",
        "sponsorship_pref": "private",
    }
    response = registered_client.post("/profile", data=data, follow_redirects=False)
    assert response.status_code == 302


def test_foreign_profile_submission(registered_client):
    data = {
        "citizenship": "foreign",
        "foreign_type": "IB Diploma",
        "foreign_total": "30",
        "foreign_subjects": "Mathematics, Physics",
        "preferred_field": "Engineering",
        "budget": "10000000",
        "sponsorship_pref": "private",
    }
    response = registered_client.post("/profile", data=data, follow_redirects=False)
    assert response.status_code == 302


def test_recommendations_after_profile(registered_client):
    registered_client.post("/profile", data={
        "citizenship": "ugandan",
        "subject_1": "Biology", "grade_1": "A",
        "subject_2": "Chemistry", "grade_2": "B",
        "subject_3": "Mathematics", "grade_3": "B",
        "preferred_field": "Computing & IT",
        "sponsorship_pref": "private",
    })
    response = registered_client.get("/recommendations")
    assert response.status_code == 200
    assert b"Your Recommendations" in response.data


def test_profile_saves_gender_and_sports(app, registered_client):
    registered_client.post("/profile", data={
        "citizenship": "ugandan",
        "subject_1": "Biology", "grade_1": "A",
        "subject_2": "Chemistry", "grade_2": "B",
        "subject_3": "Mathematics", "grade_3": "B",
        "gender": "Female",
        "sports_level": "National",
        "sports_details": "Athletics (800m)",
        "sponsorship_pref": "private",
    })
    with app.app_context():
        from models import User

        profile = User.query.filter_by(email="test@student.ug").first().profile
        assert profile.gender == "Female"
        assert profile.sports_level == "National"
        assert profile.sports_details == "Athletics (800m)"


def test_chatbot_ask(registered_client):
    response = registered_client.post("/chatbot/ask", data={"question": "Which course suits software development?"})
    assert response.status_code == 200
    assert b"answer" in response.data


def test_dashboard(registered_client):
    response = registered_client.get("/dashboard")
    assert response.status_code == 200


def test_compare(registered_client):
    response = registered_client.get("/compare")
    assert response.status_code == 200


def test_report_pdf(registered_client):
    registered_client.post("/profile", data={
        "citizenship": "ugandan",
        "subject_1": "Biology", "grade_1": "A",
        "subject_2": "Chemistry", "grade_2": "B",
        "subject_3": "Mathematics", "grade_3": "B",
        "sponsorship_pref": "private",
    })
    response = registered_client.get("/report/pdf")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"


def test_public_university_detail(app, client):
    with app.app_context():
        from models import University

        university = University.query.first()
        assert university is not None
        target_id = university.id
    response = client.get("/university/{0}".format(target_id))
    assert response.status_code == 200


def test_admin_denied_for_student(registered_client):
    response = registered_client.get("/admin/")
    assert response.status_code == 403


def test_admin_dashboard(app, client):
    client.post("/auth/login", data={
        "email": "admin@uniguide.ug",
        "password": "admin123",
    }, follow_redirects=True)
    response = client.get("/admin/")
    assert response.status_code == 200


def test_admin_add_programme(app, client, registered_client):
    with app.app_context():
        from models import Programme, University

        university = University.query.first()
        assert university is not None
        uni_id = university.id

    client.post("/auth/login", data={"email": "admin@uniguide.ug", "password": "admin123"})
    response = client.post("/admin/programmes/add", data={
        "university_id": str(uni_id),
        "name": "Bachelor of Data Science",
        "level": "Bachelor",
        "qualification_level": "UACE",
        "duration_years": "3",
        "essential_subjects": "Mathematics;Computer Science",
        "minimum_grades": "Mathematics:C",
        "principal_passes": "2",
        "cutoff_government": "12",
        "cutoff_private": "4",
        "tuition_private": "5000000",
        "admission_year": "2026/27",
        "official_source": "https://example.ug",
    }, follow_redirects=True)
    with app.app_context():
        assert Programme.query.filter_by(name="Bachelor of Data Science").first() is not None