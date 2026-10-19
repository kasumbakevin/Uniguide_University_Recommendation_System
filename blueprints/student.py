import json

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

import report as report_builder
from chatbot import answer as chatbot_answer
from courses import FIELD_KEYWORDS
from extensions import db
from models import (
    Career,
    ComparisonHistory,
    Notification,
    Programme,
    SavedRecommendation,
    StudentProfile,
    University,
)
from recommender import analyse_one, recommend

student_bp = Blueprint("student", __name__)

UACE_SUBJECTS = [
    "Biology", "Chemistry", "Physics", "Mathematics", "Economics", "Geography",
    "History", "Literature", "Divinity", "Entrepreneurship", "Computer Science",
    "Agriculture", "Fine Art", "ICT", "French", "Arabic",
]
REGIONS = ["Central", "Eastern", "Western", "Northern"]
FOREIGN_TYPES = ["CIE A-Level", "IB Diploma", "WAEC", "KCSE", "Other"]
GRADES = ["A", "B", "C", "D", "E", "F"]
GENDERS = ["Male", "Female", "Other", "Prefer not to say"]
SPORTS_LEVELS = ["School", "District", "Regional", "National", "International"]


def _get_or_create_profile():
    profile = current_user.profile
    if profile is None:
        profile = StudentProfile(user_id=current_user.id, citizenship="ugandan")
        db.session.add(profile)
        db.session.commit()
    return profile


@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    profile = _get_or_create_profile()

    if request.method == "POST":
        citizenship = request.form.get("citizenship", "ugandan")
        overall = {}

        if citizenship == "foreign":
            foreign = {
                "type": request.form.get("foreign_type", "CIE A-Level"),
                "total": request.form.get("foreign_total", "0"),
                "subjects": request.form.get("foreign_subjects", ""),
            }
            profile.foreign_qual = json.dumps(foreign, ensure_ascii=False)
            profile.uace_subjects = "{}"
            profile.uace_subsidiary = "{}"
        else:
            subjects = {}
            for index in range(1, 4):
                name = request.form.get("subject_{0}".format(index), "").strip()
                grade = request.form.get("grade_{0}".format(index), "").strip().upper()
                if name and grade in GRADES:
                    subjects[name] = grade

            subsidiary = {}
            gp = request.form.get("subsidiary_gp", "").strip().upper()
            if gp in GRADES:
                subsidiary["General Paper"] = gp
            sub_math = request.form.get("subsidiary_other", "").strip().upper()
            if sub_math in GRADES:
                subsidiary["Sub-Mathematics"] = sub_math

            if not subjects:
                flash("Please enter at least one principal subject with a grade.", "error")
                return render_template("profile.html", profile=profile, ctx=profile_form_context())

            profile.uace_subjects = json.dumps(subjects, ensure_ascii=False)
            profile.uace_subsidiary = json.dumps(subsidiary, ensure_ascii=False)
            profile.foreign_qual = "{}"

        profile.user_id = current_user.id
        profile.citizenship = citizenship
        profile.uce_summary = request.form.get("uce_summary", "")
        profile.preferred_field = request.form.get("preferred_field", "")
        profile.career_interests = json.dumps(request.form.getlist("career_interests"), ensure_ascii=False)
        profile.budget = int(request.form.get("budget", 0) or 0) or None
        profile.preferred_region = request.form.get("preferred_region", "")
        profile.sponsorship_pref = request.form.get("sponsorship_pref", "private")

        gender = request.form.get("gender", "")
        profile.gender = gender if gender in GENDERS else ""

        sports_level = request.form.get("sports_level", "")
        profile.sports_level = sports_level if sports_level in SPORTS_LEVELS else ""
        profile.sports_details = request.form.get("sports_details", "").strip()[:255]

        db.session.commit()
        flash("Your academic profile has been saved.", "success")
        return redirect(url_for("student.recommendations"))

    return render_template("profile.html", profile=profile, ctx=profile_form_context())


def profile_form_context():
    return {
        "subjects": UACE_SUBJECTS,
        "grades": GRADES,
        "regions": REGIONS,
        "foreign_types": FOREIGN_TYPES,
        "fields": list(FIELD_KEYWORDS.keys()),
        "genders": GENDERS,
        "sports_levels": SPORTS_LEVELS,
        "careers": Career.query.order_by(Career.name).all(),
        "subsidiary_opts": [
            {"name": "Sub-Mathematics", "grade": g, "label": f"Sub-Mathematics - {g}"} for g in GRADES
        ] + [
            {"name": "ICT", "grade": g, "label": f"ICT - {g}"} for g in GRADES
        ],
    }


@student_bp.route("/recommendations")
@login_required
def recommendations():
    profile = current_user.profile
    if profile is None or not profile.subjects() and profile.data.get("citizenship") != "foreign":
        flash("Please complete your academic profile first.", "info")
        return redirect(url_for("student.profile"))

    results = recommend(profile)
    eligible, borderline, not_eligible = (
        sum(1 for r in results if r["status"] == "Eligible"),
        sum(1 for r in results if r["status"] == "Borderline"),
        sum(1 for r in results if r["status"] == "Not eligible"),
    )
    saved_ids = {s.programme_id for s in current_user.saved}
    return render_template(
        "recommendations.html",
        results=results,
        eligible=eligible,
        borderline=borderline,
        not_eligible=not_eligible,
        saved_ids=saved_ids,
        profile_budget=profile.budget,
        admission_year="2026/27",
    )


@student_bp.route("/recommendations/save/<int:programme_id>", methods=["POST"])
@login_required
def save_recommendation(programme_id):
    programme = db.session.get(Programme, programme_id)
    if programme is None:
        abort(404)
    existing = current_user.saved.filter_by(programme_id=programme_id).first()
    if existing is not None:
        db.session.delete(existing)
        db.session.commit()
        flash("Removed from saved recommendations.", "info")
    else:
        analysis = analyse_one(current_user.profile, programme)
        db.session.add(SavedRecommendation(
            user_id=current_user.id,
            programme_id=programme_id,
            status=analysis["status"],
            suitability=analysis["suitability"],
            score=analysis["score"],
        ))
        db.session.commit()
        flash("Saved to your dashboard.", "success")
    return redirect(request.referrer or url_for("student.recommendations"))


@student_bp.route("/compare", methods=["GET", "POST"])
@login_required
def compare():
    selected_ids = []
    if request.method == "POST":
        selected_ids = [int(x) for x in request.form.getlist("university_ids") if x.isdigit()]
    else:
        raw = request.args.get("ids", "")
        selected_ids = [int(x) for x in raw.split(",") if x.strip().isdigit()]

    universities = University.query.filter_by(active=True).order_by(University.name).all()

    rows = []
    for university_id in selected_ids:
        university = db.session.get(University, university_id)
        if university is None:
            continue
        programmes = Programme.query.filter_by(university_id=university_id, active=True).all()
        private_fees = [p.tuition_private for p in programmes if p.tuition_private]
        gov_fees = [p.tuition_government for p in programmes if p.tuition_government]
        gov_cutoffs = [p.cutoff_government for p in programmes if p.cutoff_government]
        rows.append({
            "university": university,
            "programmes": programmes,
            "fee_min": min(private_fees) if private_fees else None,
            "fee_max": max(private_fees) if private_fees else None,
            "gov_fee_min": min(gov_fees) if gov_fees else None,
            "lowest_gov_cutoff": min(gov_cutoffs) if gov_cutoffs else None,
            "private_programmes": sum(1 for p in programmes if p.cutoff_private),
            "gov_programmes": sum(1 for p in programmes if p.cutoff_government),
        })

    if rows and current_user.is_authenticated:
        db.session.add(ComparisonHistory(
            user_id=current_user.id,
            university_ids=json.dumps(selected_ids, ensure_ascii=False),
            programme_ids="[]",
        ))
        db.session.commit()

    history = (
        ComparisonHistory.query.filter_by(user_id=current_user.id)
        .order_by(ComparisonHistory.created_at.desc())
        .limit(6)
        .all()
    )
    return render_template(
        "compare.html",
        universities=universities,
        rows=rows,
        selected_ids=set(selected_ids),
        history=history,
    )


@student_bp.route("/chatbot")
@login_required
def chatbot():
    return render_template("chatbot.html")


@student_bp.route("/chatbot/ask", methods=["POST"])
@login_required
def chatbot_ask():
    question = request.form.get("question", "") or (request.json or {}).get("question", "")
    return jsonify({"answer": chatbot_answer(question)})


@student_bp.route("/dashboard")
@login_required
def dashboard():
    profile = current_user.profile
    saved = [
        {"item": s, "programme": s.programme, "university": s.programme.university}
        for s in current_user.saved.order_by(SavedRecommendation.saved_at.desc()).all()
        if s.programme is not None
    ]
    comparisons = current_user.comparisons.order_by(ComparisonHistory.created_at.desc()).limit(6).all()
    notifications = current_user.notifications.order_by(Notification.created_at.desc()).limit(10).all()
    unread = current_user.notifications.filter_by(read=False).count()

    if profile:
        profile_data = profile.data
    else:
        profile_data = None

    return render_template(
        "dashboard.html",
        profile=profile,
        profile_data=profile_data,
        saved=saved,
        comparisons=comparisons,
        notifications=notifications,
        unread=unread,
    )


@student_bp.route("/notifications/read", methods=["POST"])
@login_required
def mark_notifications_read():
    for note in current_user.notifications.filter_by(read=False).all():
        note.read = True
    db.session.commit()
    return redirect(url_for("student.dashboard"))


@student_bp.route("/report")
@login_required
def report_html():
    profile = current_user.profile
    if profile is None:
        return redirect(url_for("student.profile"))
    results = recommend(profile)
    return render_template("report.html", results=results, profile_data=profile.data)


@student_bp.route("/report/pdf")
@login_required
def report_pdf():
    profile = current_user.profile
    if profile is None:
        return redirect(url_for("student.profile"))
    results = recommend(profile)
    buffer = report_builder.build_pdf(results, profile, current_user)
    filename = "uniguide-recommendations-{0}.pdf".format(current_user.id)
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")