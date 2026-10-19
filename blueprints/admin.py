from functools import wraps
import json
import os
import re
from glob import glob

from flask import (Blueprint, abort, current_app, flash, jsonify, redirect,
                   render_template, request, send_file, url_for)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from activity import log_activity
from extensions import db
from models import (ActivityLog, Career, ComparisonHistory, DatasetRun,
                    DatasetUpload, Enquiry, ModelVersion, Notification,
                    PredictionLog, Programme, SavedRecommendation, Setting,
                    StudentProfile, University, User)
from seed import notify_programme_update, seed_all

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "uploads")
INVENTORY_CSV = os.path.join(PROJECT_ROOT, "docs", "data_inventory.csv")
LOGO_DIR = os.path.join(PROJECT_ROOT, "static", "images", "uploads")

LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".jfif"}
MAX_LOGO_BYTES = 2 * 1024 * 1024
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return func(*args, **kwargs)

    return wrapper


def _page_arg():
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    return page


def _per_page():
    default = Setting.get_int("items_per_page", 10)
    return min(max(default, 5), 100)


def _paginate(query, page=None):
    return query.paginate(page=page or _page_arg(), per_page=_per_page(), error_out=False)


def _clean_search(value):
    return (value or "").strip()[:80]


def _as_int(raw, default=None):
    try:
        return int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return default


def _valid_url(value):
    if not value:
        return True
    return bool(re.match(r"^(https?:\/\/|www\.)[^\s]+$", value.strip(), re.IGNORECASE))


def _require_confirm(record_name):
    """Deletes must echo the record name back from the confirmation dialog."""
    typed = (request.form.get("confirm_name") or "").strip()
    if typed.lower() != (record_name or "").strip().lower():
        flash("Deletion cancelled — the confirmation did not match '{0}'.".format(record_name), "error")
        return False
    return True


@admin_bp.route("/")
@admin_required
def dashboard():
    programmes = Programme.query
    active_programmes = programmes.filter_by(active=True)
    requirement_filter = db.or_(
        Programme.principal_passes.isnot(None),
        Programme.minimum_grades.isnot(None),
        Programme.cutoff_government.isnot(None),
        Programme.cutoff_private.isnot(None),
    )
    stats = {
        "universities": University.query.count(),
        "active_universities": University.query.filter_by(active=True).count(),
        "programmes": programmes.filter_by(active=True).count(),
        "total_programmes": programmes.count(),
        "requirements": programmes.filter(requirement_filter).count(),
        "careers": Career.query.count(),
        "students": User.query.filter_by(role="student").count(),
        "admins": User.query.filter_by(role="admin").count(),
        "saved": SavedRecommendation.query.count(),
        "enquiries": Enquiry.query.count(),
        "datasets": DatasetUpload.query.count() + DatasetRun.query.count(),
        "uploads": DatasetUpload.query.count(),
        "runs": DatasetRun.query.count(),
        "settings": Setting.query.count(),
    }
    recent = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(8).all()
    return render_template("admin/dashboard.html", stats=stats, recent=recent)


@admin_bp.route("/universities")
@admin_required
def universities():
    query = University.query
    term = _clean_search(request.args.get("q", ""))
    if term:
        pattern = "%{0}%".format(term)
        query = query.filter(db.or_(University.name.ilike(pattern),
                                    University.region.ilike(pattern),
                                    University.district.ilike(pattern)))
    status = request.args.get("status", "")
    if status in ("active", "inactive"):
        query = query.filter_by(active=(status == "active"))
    sort = request.args.get("sort", "name")
    order = {
        "name": University.name,
        "region": University.region,
        "type": University.institution_type,
        "district": University.district,
    }.get(sort, University.name)
    if request.args.get("dir") == "desc":
        order = order.desc()
    page_obj = _paginate(query.order_by(order))
    return render_template("admin/universities.html", universities=page_obj.items,
                           page_obj=page_obj, q=term, status=status, sort=sort,
                           direction=request.args.get("dir", "asc"))


def _university_from_form(university):
    name = request.form.get("name", "").strip()
    website = request.form.get("website", "").strip()
    application_link = request.form.get("application_link", "").strip()
    errors = []
    if not name:
        errors.append("University name is required.")
    if len(name) > 160:
        errors.append("University name must be 160 characters or fewer.")
    if not _valid_url(website):
        errors.append("Website must be a valid URL starting with http:// or https://.")
    if not _valid_url(application_link):
        errors.append("Application link must be a valid URL starting with http:// or https://.")
    if errors:
        for error in errors:
            flash(error, "error")
        return None, errors

    if university is None:
        university = University(name=name)
        db.session.add(university)
    else:
        university.name = name
    image = request.form.get("image", "").strip()
    if image and (os.path.isabs(image) or ".." in image.split("/") or "://" in image
                  or "\\" in image):
        errors.append("Logo filename must be a plain file name inside static/images "
                      "without path separators.")
        flash(errors[-1], "error")
        return None, errors
    university.institution_type = request.form.get("institution_type", "public")
    university.region = request.form.get("region", "").strip()
    university.district = request.form.get("district", "").strip()
    university.location = request.form.get("location", "").strip()
    university.established = _as_int(request.form.get("established"))
    university.website = website
    university.application_link = application_link
    university.image = request.form.get("image", "").strip()
    university.active = request.form.get("active") == "on"
    return university, []


@admin_bp.route("/universities/add", methods=["GET", "POST"])
@admin_required
def university_add():
    if request.method == "POST":
        university, errors = _university_from_form(None)
        if errors:
            return render_template("admin/university_form.html", university=None,
                                   form_data=request.form)
        db.session.commit()
        log_activity("create", "university", university.id, {"name": university.name})
        flash("University added.", "success")
        return redirect(url_for("admin.universities"))
    return render_template("admin/university_form.html", university=None, form_data={})


@admin_bp.route("/universities/<int:university_id>/edit", methods=["GET", "POST"])
@admin_required
def university_edit(university_id):
    university = db.session.get(University, university_id)
    if university is None:
        abort(404)
    if request.method == "POST":
        updated, errors = _university_from_form(university)
        if errors:
            return render_template("admin/university_form.html", university=university,
                                   form_data=request.form)
        db.session.commit()
        log_activity("update", "university", university.id, {"name": university.name})
        flash("University updated.", "success")
        return redirect(url_for("admin.universities"))
    return render_template("admin/university_form.html", university=university, form_data={})


@admin_bp.route("/universities/<int:university_id>/toggle", methods=["POST"])
@admin_required
def university_toggle(university_id):
    university = db.session.get(University, university_id)
    if university is None:
        abort(404)
    university.active = not university.active
    db.session.commit()
    action = "activate" if university.active else "deactivate"
    log_activity(action, "university", university.id, {"name": university.name})
    flash("University {0} {1}.".format(university.name,
                                       "activated" if university.active else "deactivated"),
          "success")
    return redirect(url_for("admin.universities"))


@admin_bp.route("/universities/<int:university_id>/logo", methods=["POST"])
@admin_required
def university_logo_upload(university_id):
    university = db.session.get(University, university_id)
    if university is None:
        abort(404)
    upload = request.files.get("logo")
    if upload is None or upload.filename == "":
        flash("Choose a logo file to upload.", "error")
        return redirect(url_for("admin.university_edit", university_id=university_id))

    original = secure_filename(upload.filename)
    extension = os.path.splitext(original)[1].lower()
    if extension not in LOGO_EXTENSIONS:
        flash("Logo must be an image file ({0}).".format(", ".join(sorted(LOGO_EXTENSIONS))), "error")
        return redirect(url_for("admin.university_edit", university_id=university_id))
    data = upload.read()
    if len(data) > MAX_LOGO_BYTES:
        flash("Logo is too large. Maximum size is 2 MB.", "error")
        return redirect(url_for("admin.university_edit", university_id=university_id))
    if not data:
        flash("The uploaded logo file is empty.", "error")
        return redirect(url_for("admin.university_edit", university_id=university_id))

    # SVG uploads can contain scripts: store them only with a safe prefix and never inline them.
    stored = "u{0}_{1}{2}".format(university.id, secure_filename(os.path.splitext(original)[0])[:40] or "logo", extension)
    if extension == ".svg":
        stored = stored.replace(".svg", "_img.svg")
        head = data[:512].lstrip().lower()
        if b"<script" in data.lower() or not head.startswith(b"<?xml") and not head.startswith(b"<svg"):
            flash("This SVG appears to contain scripts and was rejected.", "error")
            return redirect(url_for("admin.university_edit", university_id=university_id))
    os.makedirs(LOGO_DIR, exist_ok=True)
    target = os.path.join(LOGO_DIR, stored)
    with open(target, "wb") as handle:
        handle.write(data)

    old = university.image
    university.image = "uploads/{0}".format(stored)
    db.session.commit()
    log_activity("update", "university", university.id,
                 {"name": university.name, "logo": stored})
    flash("Logo updated for {0}.".format(university.name), "success")
    if old and old.startswith("uploads/"):
        old_path = os.path.join(PROJECT_ROOT, "static", "images", old)
        if os.path.abspath(old_path).startswith(os.path.abspath(LOGO_DIR)) and os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
    return redirect(url_for("admin.university_edit", university_id=university_id))


@admin_bp.route("/universities/<int:university_id>/delete", methods=["POST"])
@admin_required
def university_delete(university_id):
    university = db.session.get(University, university_id)
    if university is None:
        abort(404)
    if not _require_confirm(university.name):
        return redirect(url_for("admin.universities"))
    programme_ids = [p.id for p in university.programmes.all()]
    saved_count = SavedRecommendation.query.filter(
        SavedRecommendation.programme_id.in_(programme_ids)).count() if programme_ids else 0
    count = len(programme_ids)
    try:
        SavedRecommendation.query.filter(SavedRecommendation.programme_id.in_(programme_ids)).delete(
            synchronize_session=False)
        Programme.query.filter_by(university_id=university_id).delete()
        db.session.delete(university)
        db.session.commit()
        log_activity("delete", "university", university_id,
                     {"name": university.name, "programmes": count, "saved_recommendations": saved_count})
        flash("Deleted {0} and its {1} programme(s). {2} saved recommendation(s) linked to "
              "those programmes were also removed.".format(university.name, count, saved_count),
              "info")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash("Could not delete {0}: {1}".format(university.name, exc), "error")
    return redirect(url_for("admin.universities"))


@admin_bp.route("/programmes")
@admin_required
def programmes():
    query = Programme.query
    term = _clean_search(request.args.get("q", ""))
    if term:
        pattern = "%{0}%".format(term)
        query = query.join(University, isouter=True).filter(
            db.or_(Programme.name.ilike(pattern),
                   University.name.ilike(pattern),
                   Programme.level.ilike(pattern)))
    status = request.args.get("status", "")
    if status in ("active", "inactive"):
        query = query.filter(Programme.active == (status == "active"))
    level = request.args.get("level", "")
    if level:
        query = query.filter(Programme.level == level)
    university_id = _as_int(request.args.get("university", ""))
    if university_id:
        query = query.filter(Programme.university_id == university_id)
    sort = request.args.get("sort", "name")
    order = {
        "name": Programme.name,
        "level": Programme.level,
        "year": Programme.admission_year,
        "tuition": Programme.tuition_private,
        "cutoff": Programme.cutoff_government,
    }.get(sort, Programme.name)
    if request.args.get("dir") == "desc":
        order = order.desc()
    page_obj = _paginate(query.order_by(order))
    return render_template("admin/programmes.html", programmes=page_obj.items,
                           page_obj=page_obj, q=term, status=status, sort=sort,
                           level=level, university=university_id,
                           direction=request.args.get("dir", "asc"),
                           universities=University.query.order_by(University.name).all())


def _programme_from_form(programme):
    def num(field):
        raw = request.form.get(field, "").strip()
        if not raw:
            return None
        try:
            return int(float(raw))
        except ValueError:
            return None

    name = request.form.get("name", "").strip()
    university_id = _as_int(request.form.get("university_id"))
    errors = []
    if not name:
        errors.append("Programme name is required.")
    if len(name) > 200:
        errors.append("Programme name must be 200 characters or fewer.")
    if not university_id or db.session.get(University, university_id) is None:
        errors.append("Choose a valid university for this programme.")
    tuition_private = num("tuition_private")
    tuition_government = num("tuition_government")
    if tuition_private is not None and tuition_private < 0:
        errors.append("Private tuition fee cannot be negative.")
    if tuition_government is not None and tuition_government < 0:
        errors.append("Government tuition fee cannot be negative.")
    official_source = request.form.get("official_source", "").strip()
    if not _valid_url(official_source):
        errors.append("Official source must be a valid URL starting with http:// or https://.")
    admission_year = request.form.get("admission_year", "").strip()
    if admission_year and not re.match(r"^\d{4}/\d{2}$", admission_year):
        errors.append("Admission year must look like 2026/27.")
    if errors:
        for error in errors:
            flash(error, "error")
        return None, errors

    if programme is None:
        programme = Programme()
        db.session.add(programme)

    programme.university_id = university_id
    programme.name = name
    programme.level = request.form.get("level", "Bachelor")
    programme.qualification_level = request.form.get("qualification_level", "UACE")
    programme.duration_years = num("duration_years") or 3
    programme.essential_subjects = request.form.get("essential_subjects", "")
    programme.relevant_subjects = request.form.get("relevant_subjects", "")
    programme.minimum_grades = request.form.get("minimum_grades", "")
    programme.principal_passes = num("principal_passes") or 2
    programme.uce_requirement = request.form.get("uce_requirement", "") or None
    programme.cutoff_government = num("cutoff_government")
    programme.cutoff_private = num("cutoff_private")
    programme.foreign_min_total = num("foreign_min_total")
    programme.tuition_government = tuition_government
    programme.tuition_private = tuition_private
    programme.international_eligible = request.form.get("international_eligible") == "on"
    programme.admission_year = admission_year or Setting.get("default_admission_year", "2026/27")
    programme.official_source = official_source
    programme.active = request.form.get("active") != "off"
    return programme, []


@admin_bp.route("/programmes/add", methods=["GET", "POST"])
@admin_required
def programme_add():
    if request.method == "POST":
        programme, errors = _programme_from_form(None)
        if errors:
            return render_template("admin/programme_form.html", programme=None,
                                   universities=University.query.order_by(University.name).all(),
                                   form_data=request.form)
        db.session.commit()
        notify_programme_update(programme, "A new programme '{}' was added to the database.".format(programme.name))
        log_activity("create", "programme", programme.id,
                     {"name": programme.name, "university": programme.university.name})
        flash("Programme added.", "success")
        return redirect(url_for("admin.programmes"))
    return render_template(
        "admin/programme_form.html",
        programme=None,
        universities=University.query.order_by(University.name).all(),
        form_data={},
    )


@admin_bp.route("/programmes/<int:programme_id>/edit", methods=["GET", "POST"])
@admin_required
def programme_edit(programme_id):
    programme = db.session.get(Programme, programme_id)
    if programme is None:
        abort(404)
    if request.method == "POST":
        updated, errors = _programme_from_form(programme)
        if errors:
            return render_template("admin/programme_form.html", programme=programme,
                                   universities=University.query.order_by(University.name).all(),
                                   form_data=request.form)
        db.session.commit()
        notify_programme_update(programme, "Entry information for '{}' was updated.".format(programme.name))
        log_activity("update", "programme", programme.id,
                     {"name": programme.name, "university": programme.university.name})
        flash("Programme updated.", "success")
        return redirect(url_for("admin.programmes"))
    return render_template(
        "admin/programme_form.html",
        programme=programme,
        universities=University.query.order_by(University.name).all(),
        form_data={},
    )


@admin_bp.route("/programmes/<int:programme_id>/view")
@admin_required
def programme_view(programme_id):
    programme = db.session.get(Programme, programme_id)
    if programme is None:
        abort(404)
    saved_count = SavedRecommendation.query.filter_by(programme_id=programme_id).count()
    return render_template("admin/programme_detail.html", programme=programme,
                           saved_count=saved_count)


@admin_bp.route("/programmes/<int:programme_id>/toggle", methods=["POST"])
@admin_required
def programme_toggle(programme_id):
    programme = db.session.get(Programme, programme_id)
    if programme is None:
        abort(404)
    programme.active = not programme.active
    db.session.commit()
    log_activity("activate" if programme.active else "deactivate", "programme", programme.id,
                 {"name": programme.name})
    flash("Programme {0} {1}.".format(programme.name,
                                      "activated" if programme.active else "deactivated"), "success")
    return redirect(url_for("admin.programmes"))


@admin_bp.route("/programmes/<int:programme_id>/delete", methods=["POST"])
@admin_required
def programme_delete(programme_id):
    programme = db.session.get(Programme, programme_id)
    if programme is None:
        abort(404)
    if not _require_confirm(programme.name):
        return redirect(url_for("admin.programmes"))
    saved_count = SavedRecommendation.query.filter_by(programme_id=programme_id).count()
    try:
        SavedRecommendation.query.filter_by(programme_id=programme_id).delete()
        db.session.delete(programme)
        db.session.commit()
        log_activity("delete", "programme", programme_id,
                     {"name": programme.name, "saved_recommendations": saved_count})
        flash("Deleted {0}. {1} saved recommendation(s) for this programme were also "
              "removed.".format(programme.name, saved_count), "info")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash("Could not delete {0}: {1}".format(programme.name, exc), "error")
    return redirect(url_for("admin.programmes"))


@admin_bp.route("/requirements")
@admin_required
def requirements():
    """Admission requirements view: every programme's entry rules in one table."""
    query = Programme.query.join(University, isouter=True)
    term = _clean_search(request.args.get("q", ""))
    if term:
        pattern = "%{0}%".format(term)
        query = query.filter(db.or_(Programme.name.ilike(pattern),
                                    University.name.ilike(pattern),
                                    Programme.essential_subjects.ilike(pattern),
                                    Programme.minimum_grades.ilike(pattern)))
    year = _clean_search(request.args.get("year", ""))
    if year:
        query = query.filter(Programme.admission_year == year)
    incomplete = request.args.get("incomplete") == "1"
    if incomplete:
        query = query.filter(db.or_(Programme.essential_subjects.is_(None),
                                    Programme.essential_subjects == "",
                                    Programme.minimum_grades.is_(None),
                                    Programme.minimum_grades == "",
                                    Programme.principal_passes.is_(None)))
    query = query.filter(db.or_(Programme.principal_passes.isnot(None),
                                Programme.minimum_grades.isnot(None),
                                Programme.essential_subjects.isnot(None)))
    page_obj = _paginate(query.order_by(Programme.admission_year.desc(), Programme.name))
    years = [row[0] for row in db.session.query(Programme.admission_year).distinct().all()
             if row[0]]
    return render_template("admin/requirements.html", requirements=page_obj.items,
                           page_obj=page_obj, q=term, year=year, years=years,
                           incomplete=incomplete)


@admin_bp.route("/careers")
@admin_required
def careers():
    query = Career.query
    term = _clean_search(request.args.get("q", ""))
    if term:
        pattern = "%{0}%".format(term)
        query = query.filter(db.or_(Career.name.ilike(pattern),
                                    Career.description.ilike(pattern)))
    page_obj = _paginate(query.order_by(Career.name))
    return render_template("admin/careers.html", careers=page_obj.items,
                           page_obj=page_obj, q=term)


def _career_from_form(career):
    name = request.form.get("name", "").strip()
    if not name:
        flash("Career name is required.", "error")
        return None, False
    if len(name) > 160:
        flash("Career name must be 160 characters or fewer.", "error")
        return None, False
    if career is None:
        career = Career(name=name)
        db.session.add(career)
    else:
        career.name = name
    career.description = request.form.get("description", "").strip()
    career.required_subjects = request.form.get("required_subjects", "").strip()
    career.skills = request.form.get("skills", "").strip()
    career.pathways = request.form.get("pathways", "").strip()
    return career, True


@admin_bp.route("/careers/add", methods=["GET", "POST"])
@admin_required
def career_add():
    if request.method == "POST":
        career, ok = _career_from_form(None)
        if not ok:
            return render_template("admin/career_form.html", career=None, form_data=request.form)
        db.session.commit()
        log_activity("create", "career", career.id, {"name": career.name})
        flash("Career added.", "success")
        return redirect(url_for("admin.careers"))
    return render_template("admin/career_form.html", career=None, form_data={})


@admin_bp.route("/careers/<int:career_id>/edit", methods=["GET", "POST"])
@admin_required
def career_edit(career_id):
    career = db.session.get(Career, career_id)
    if career is None:
        abort(404)
    if request.method == "POST":
        updated, ok = _career_from_form(career)
        if not ok:
            return render_template("admin/career_form.html", career=career, form_data=request.form)
        db.session.commit()
        log_activity("update", "career", career.id, {"name": career.name})
        flash("Career updated.", "success")
        return redirect(url_for("admin.careers"))
    return render_template("admin/career_form.html", career=career, form_data={})


@admin_bp.route("/careers/<int:career_id>/delete", methods=["POST"])
@admin_required
def career_delete(career_id):
    career = db.session.get(Career, career_id)
    if career is None:
        abort(404)
    if not _require_confirm(career.name):
        return redirect(url_for("admin.careers"))
    linked = career.programmes.count()
    try:
        db.session.delete(career)
        db.session.commit()
        log_activity("delete", "career", career_id, {"name": career.name, "linked_programmes": linked})
        flash("Deleted career '{0}'. {1} programme link(s) to this career were "
              "removed.".format(career.name, linked), "info")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash("Could not delete {0}: {1}".format(career.name, exc), "error")
    return redirect(url_for("admin.careers"))


@admin_bp.route("/users")
@admin_required
def users():
    query = User.query
    term = _clean_search(request.args.get("q", ""))
    if term:
        pattern = "%{0}%".format(term)
        query = query.filter(db.or_(User.name.ilike(pattern),
                                    User.email.ilike(pattern),
                                    User.username.ilike(pattern)))
    role = request.args.get("role", "")
    if role in ("admin", "student"):
        query = query.filter_by(role=role)
    page_obj = _paginate(query.order_by(User.created_at.desc()))
    return render_template("admin/users.html", users=page_obj.items,
                           page_obj=page_obj, q=term, role=role)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def user_edit(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = (request.form.get("username", "").strip() or None)
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", user.role)
        errors = []
        if not name:
            errors.append("Name is required.")
        if "@" not in email or "." not in email.split("@")[-1]:
            errors.append("Enter a valid email address.")
        if username and not re.match(r"^[A-Za-z0-9_.-]{3,80}$", username):
            errors.append("Username must be 3-80 characters using letters, numbers, _ . or -.")
        clash = User.query.filter(User.email == email).filter(User.id != user.id).first()
        if clash:
            errors.append("That email is already used by another account.")
        if username:
            clash = User.query.filter(User.username == username).filter(User.id != user.id).first()
            if clash:
                errors.append("That username is already taken.")
        if role not in ("admin", "student"):
            errors.append("Unknown role.")
        if role == "student" and user.role == "admin" and _admin_count() <= 1:
            errors.append("This is the last administrator account — its role cannot be changed.")
        wants_active = request.form.get("active") == "on"
        if not wants_active:
            if user.id == current_user.id:
                errors.append("You cannot deactivate your own account.")
            elif user.role == "admin" and _admin_count() <= 1 and user.active is not False:
                errors.append("The last administrator account cannot be deactivated.")
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("admin/user_form.html", user=user, form_data=request.form)
        user.name = name
        user.username = username
        user.email = email
        user.role = role
        user.active = wants_active
        db.session.commit()
        log_activity("update", "user", user.id,
                     {"name": user.name, "role": user.role, "active": user.active})
        flash("User updated.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", user=user, form_data={})


def _admin_count():
    return User.query.filter_by(role="admin").count()


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def user_toggle(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for("admin.users"))
    if user.role == "admin" and _admin_count() <= 1:
        flash("The last administrator account cannot be deactivated.", "error")
        return redirect(url_for("admin.users"))
    user.active = not (user.active is not False)
    db.session.commit()
    log_activity("activate" if user.active else "deactivate", "user", user.id,
                 {"name": user.name})
    flash("Account for {0} {1}.".format(user.name,
                                         "activated" if user.active else "deactivated"), "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def user_delete(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.users"))
    if user.role == "admin" and _admin_count() <= 1:
        flash("The last administrator account cannot be deleted.", "error")
        return redirect(url_for("admin.users"))
    if not _require_confirm(user.name):
        return redirect(url_for("admin.users"))
    try:
        SavedRecommendation.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        ComparisonHistory.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        Notification.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        PredictionLog.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        StudentProfile.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        db.session.delete(user)
        db.session.commit()
        log_activity("delete", "user", user_id, {"name": user.name, "role": user.role})
        flash("Deleted account {0} and its personal data.".format(user.name), "info")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash("Could not delete {0}: {1}".format(user.name, exc), "error")
    return redirect(url_for("admin.users"))


@admin_bp.route("/enquiries")
@admin_required
def enquiries():
    items = Enquiry.query.order_by(Enquiry.created_at.desc()).all()
    unread = Enquiry.query.filter(Enquiry.read.isnot(True)).count()
    return render_template("admin/enquiries.html", enquiries=items, unread=unread)


@admin_bp.route("/enquiries/<int:enquiry_id>/toggle", methods=["POST"])
@admin_required
def enquiry_toggle(enquiry_id):
    enquiry = db.session.get(Enquiry, enquiry_id)
    if enquiry is None:
        abort(404)
    enquiry.read = not enquiry.read
    db.session.commit()
    log_activity("update", "enquiry", enquiry.id,
                 {"subject": enquiry.subject or enquiry.name,
                  "state": "read" if enquiry.read else "unread"})
    flash("Enquiry marked as {0}.".format("read" if enquiry.read else "unread"), "success")
    return redirect(url_for("admin.enquiries"))


@admin_bp.route("/enquiries/<int:enquiry_id>/delete", methods=["POST"])
@admin_required
def enquiry_delete(enquiry_id):
    enquiry = db.session.get(Enquiry, enquiry_id)
    if enquiry is None:
        abort(404)
    label = enquiry.subject or enquiry.name
    if not _require_confirm(label):
        return redirect(url_for("admin.enquiries"))
    try:
        db.session.delete(enquiry)
        db.session.commit()
        log_activity("delete", "enquiry", enquiry_id, {"subject": label})
        flash("Enquiry deleted.", "info")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash("Could not delete the enquiry: {0}".format(exc), "error")
    return redirect(url_for("admin.enquiries"))


@admin_bp.route("/import")
@admin_required
def import_data():
    return render_template("admin/import.html")


@admin_bp.route("/import/run", methods=["POST"])
@admin_required
def import_run():
    try:
        before = (University.query.count(), Programme.query.count(), Career.query.count())
        seed_all()
        after = (University.query.count(), Programme.query.count(), Career.query.count())
        log_activity("import", "dataset", None, {
            "mode": "upsert",
            "before": {"universities": before[0], "programmes": before[1], "careers": before[2]},
            "after": {"universities": after[0], "programmes": after[1], "careers": after[2]},
        })
        flash("Dataset re-imported. {0} universities, {1} programmes, {2} careers are now in the "
              "database. Existing records were updated, nothing was deleted.".format(*after), "success")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash("Import failed: {0}".format(exc), "error")
    return redirect(url_for("admin.import_data"))

SETTINGS_TABS = [
    ("general", "General"),
    ("account", "Admin Account"),
    ("programmes", "Universities & Programmes"),
    ("recommendation", "Recommendation"),
    ("dataset", "Dataset Management"),
    ("appearance", "Appearance"),
    ("logs", "Activity Logs"),
]

DATE_FORMATS = {
    "%d %B %Y": "18 October 2026",
    "%d/%m/%Y": "18/10/2026",
    "%Y-%m-%d": "2026-10-18",
    "%d %b %Y": "18 Oct 2026",
}

ACCENT_CHOICES = ["#18794E", "#1B7F5A", "#12345A", "#8A5A05", "#7C3AED", "#B91C1C", "#0E7490"]


def _settings_context(tab):
    return {
        "tabs": SETTINGS_TABS,
        "active_tab": tab,
        "date_formats": DATE_FORMATS,
        "accent_choices": ACCENT_CHOICES,
    }


def _save_settings(pairs, group):
    for key, value in pairs.items():
        Setting.set(key, value, group=group, user_id=current_user.id)
    db.session.commit()


@admin_bp.route("/settings")
@admin_required
def settings():
    tab = request.args.get("tab", "general")
    if tab not in [name for name, _ in SETTINGS_TABS]:
        tab = "general"
    context = _settings_context(tab)
    from models import DEFAULT_SETTINGS

    context["values"] = {key: Setting.get(key, default)
                         for key, default in DEFAULT_SETTINGS.items()}
    context["current_email"] = current_user.email
    if tab == "account":
        context["admin_user"] = current_user
    if tab == "recommendation":
        context["eligibility_rules"] = _eligibility_rule_rows()
    if tab == "dataset":
        context["dataset_summary"] = _dataset_summary()
    if tab == "logs":
        context["recent"] = ActivityLog.query.order_by(
            ActivityLog.created_at.desc()).limit(15).all()
    return render_template("admin/settings.html", **context)


def _eligibility_rule_rows():
    """Programme-level admission rules. Read-only in settings: never made configurable."""
    rows = Programme.query.filter(
        db.or_(Programme.principal_passes.isnot(None),
               Programme.minimum_grades.isnot(None))
    ).order_by(Programme.university_id, Programme.name).limit(15).all()
    return [{
        "programme": programme,
        "university": programme.university.name if programme.university else "",
    } for programme in rows]


def _dataset_summary():
    return {
        "universities": University.query.count(),
        "programmes": Programme.query.count(),
        "careers": Career.query.count(),
        "uploads": DatasetUpload.query.order_by(DatasetUpload.uploaded_at.desc()).limit(10).all(),
        "runs": DatasetRun.query.order_by(DatasetRun.created_at.desc()).limit(10).all(),
        "default_year": Setting.get("default_admission_year", "2026/27"),
    }


@admin_bp.route("/settings/general", methods=["POST"])
@admin_required
def settings_general():
    site_name = request.form.get("site_name", "").strip()
    contact_email = request.form.get("contact_email", "").strip().lower()
    items_per_page = _as_int(request.form.get("items_per_page"), 10)
    date_format = request.form.get("date_format", "%d %B %Y")
    if not site_name:
        flash("System name is required.", "error")
        return redirect(url_for("admin.settings", tab="general"))
    if contact_email and ("@" not in contact_email or "." not in contact_email.split("@")[-1]):
        flash("Contact email is not valid.", "error")
        return redirect(url_for("admin.settings", tab="general"))
    if items_per_page is None or not 5 <= items_per_page <= 100:
        flash("Default page size must be between 5 and 100.", "error")
        return redirect(url_for("admin.settings", tab="general"))
    if date_format not in DATE_FORMATS:
        date_format = "%d %B %Y"
    _save_settings({
        "site_name": site_name[:80],
        "site_description": request.form.get("site_description", "").strip()[:300],
        "contact_email": contact_email[:120],
        "contact_phone": request.form.get("contact_phone", "").strip()[:40],
        "homepage_image": request.form.get("homepage_image", "").strip()[:120],
        "items_per_page": str(items_per_page),
        "date_format": date_format,
    }, "general")
    log_activity("setting", "settings", None, {"section": "general", "site_name": site_name[:80]})
    flash("General settings saved.", "success")
    return redirect(url_for("admin.settings", tab="general"))


@admin_bp.route("/settings/account", methods=["POST"])
@admin_required
def settings_account():
    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip() or None
    email = request.form.get("email", "").strip().lower()
    errors = []
    if not name:
        errors.append("Name is required.")
    if "@" not in email or "." not in email.split("@")[-1]:
        errors.append("Enter a valid email address.")
    if username and not re.match(r"^[A-Za-z0-9_.-]{3,80}$", username):
        errors.append("Username must be 3-80 characters using letters, numbers, _ . or -.")
    clash = User.query.filter(User.email == email).filter(User.id != current_user.id).first()
    if clash:
        errors.append("That email is already used by another account.")
    if username:
        clash = User.query.filter(User.username == username).filter(User.id != current_user.id).first()
        if clash:
            errors.append("That username is already taken.")
    if errors:
        for error in errors:
            flash(error, "error")
        return redirect(url_for("admin.settings", tab="account"))
    before = current_user.email
    current_user.name = name
    current_user.username = username
    current_user.email = email
    db.session.commit()
    log_activity("update", "user", current_user.id,
                 {"name": name, "email": email, "previous_email": before})
    flash("Admin profile updated.", "success")
    return redirect(url_for("admin.settings", tab="account"))


@admin_bp.route("/settings/password", methods=["POST"])
@admin_required
def settings_password():
    from werkzeug.security import check_password_hash, generate_password_hash

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    if not check_password_hash(current_user.password_hash, current_password):
        flash("Your current password is incorrect.", "error")
        return redirect(url_for("admin.settings", tab="account"))
    if len(new_password) < 8:
        flash("New password must be at least 8 characters.", "error")
        return redirect(url_for("admin.settings", tab="account"))
    if not re.search(r"[A-Za-z]", new_password) or not re.search(r"\d", new_password):
        flash("New password must contain at least one letter and one number.", "error")
        return redirect(url_for("admin.settings", tab="account"))
    if new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for("admin.settings", tab="account"))
    if check_password_hash(current_user.password_hash, new_password):
        flash("Choose a password you have not used before.", "error")
        return redirect(url_for("admin.settings", tab="account"))
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    log_activity("password_change", "user", current_user.id, {"name": current_user.name})
    flash("Password changed successfully.", "success")
    return redirect(url_for("admin.settings", tab="account"))


@admin_bp.route("/settings/programmes", methods=["POST"])
@admin_required
def settings_programmes():
    default_year = request.form.get("default_admission_year", "").strip()
    if not re.match(r"^\d{4}/\d{2}$", default_year):
        flash("Default admission year must look like 2026/27.", "error")
        return redirect(url_for("admin.settings", tab="programmes"))
    fields = [f.strip() for f in request.form.get("preference_fields", "").split(",") if f.strip()]
    if not fields:
        flash("List at least one student preference field.", "error")
        return redirect(url_for("admin.settings", tab="programmes"))
    if len(fields) > 30:
        flash("Keep the preference field list to 30 items or fewer.", "error")
        return redirect(url_for("admin.settings", tab="programmes"))
    _save_settings({
        "default_admission_year": default_year,
        "preference_fields": ", ".join(fields)[:600],
        "programmes_active_by_default": "1" if request.form.get("active_default") == "on" else "0",
    }, "programmes")
    log_activity("setting", "settings", None,
                 {"section": "programmes", "default_admission_year": default_year})
    flash("University and programme settings saved.", "success")
    return redirect(url_for("admin.settings", tab="programmes"))


RECOMMENDATION_WEIGHTS = ("weight_essential", "weight_relevant", "weight_other",
                          "weight_subsidiary")
RECOMMENDATION_KEYS = RECOMMENDATION_WEIGHTS + ("budget_tolerance_pct",)
RECOMMENDATION_TOGGLES = ("use_budget_match", "use_region_match", "use_career_match",
                          "use_fee_preference")


@admin_bp.route("/settings/recommendation", methods=["POST"])
@admin_required
def settings_recommendation():
    values = {}
    for key in RECOMMENDATION_KEYS:
        raw = request.form.get(key, "")
        try:
            number = float(raw)
        except (TypeError, ValueError):
            flash("'{0}' must be a number.".format(key.replace("_", " ")), "error")
            return redirect(url_for("admin.settings", tab="recommendation"))
        if number < 0:
            flash("Ranking weights and tolerance must not be negative.", "error")
            return redirect(url_for("admin.settings", tab="recommendation"))
        if key in RECOMMENDATION_WEIGHTS and number > 20:
            flash("Ranking weights must be between 0 and 20.", "error")
            return redirect(url_for("admin.settings", tab="recommendation"))
        values[key] = str(number)
    tolerance = float(values["budget_tolerance_pct"])
    if tolerance > 200:
        flash("Budget tolerance must be 200% or less.", "error")
        return redirect(url_for("admin.settings", tab="recommendation"))
    for key in RECOMMENDATION_TOGGLES:
        values[key] = "1" if request.form.get(key) == "on" else "0"
    _save_settings(values, "recommendation")
    log_activity("setting", "settings", None, {"section": "recommendation"})
    flash("Recommendation settings saved. Compulsory admission rules (principal passes, "
          "essential subjects, minimum grades and cut-offs) are unchanged.", "success")
    return redirect(url_for("admin.settings", tab="recommendation"))


@admin_bp.route("/settings/appearance", methods=["POST"])
@admin_required
def settings_appearance():
    theme = request.form.get("theme", "light")
    if theme not in ("light", "dark"):
        theme = "light"
    accent = request.form.get("accent_color", "#18794E").strip()
    if not re.match(r"^#[0-9A-Fa-f]{6}$", accent):
        accent = "#18794E"
    homepage_image = request.form.get("homepage_image", "").strip()
    if homepage_image and (".." in homepage_image or "\\" in homepage_image or "://" in homepage_image):
        flash("Homepage image must be a plain file name inside static/images.", "error")
        return redirect(url_for("admin.settings", tab="appearance"))
    _save_settings({
        "theme": theme,
        "accent_color": accent,
        "homepage_image": homepage_image[:120],
        "show_university_logos": "1" if request.form.get("show_logos") == "on" else "0",
        "sidebar_compact": "1" if request.form.get("sidebar_compact") == "on" else "0",
        "homepage_title": request.form.get("homepage_title", "").strip()[:80],
    }, "appearance")
    log_activity("setting", "settings", None, {"section": "appearance", "theme": theme,
                                               "accent": accent})
    flash("Appearance settings saved.", "success")
    return redirect(url_for("admin.settings", tab="appearance"))


@admin_bp.route("/logs")
@admin_required
def activity_logs():
    query = ActivityLog.query
    action = request.args.get("action", "")
    if action:
        query = query.filter_by(action=action)
    entity = request.args.get("entity", "")
    if entity:
        query = query.filter_by(entity=entity)
    user_id = _as_int(request.args.get("user", ""))
    if user_id:
        query = query.filter_by(user_id=user_id)
    page_obj = _paginate(query.order_by(ActivityLog.created_at.desc()))
    actions = [row[0] for row in db.session.query(ActivityLog.action).distinct().all()]
    entities = [row[0] for row in db.session.query(ActivityLog.entity).distinct().all()
                if row[0]]
    admins = User.query.order_by(User.name).all()
    return render_template("admin/logs.html", logs=page_obj.items, page_obj=page_obj,
                           actions=actions, entities=entities, admins=admins,
                           selected_action=action, selected_entity=entity,
                           selected_user=user_id)


def _list_runs():
    runs = []
    if os.path.isdir(PROCESSED_DIR):
        for name in sorted(os.listdir(PROCESSED_DIR), reverse=True):
            path = os.path.join(PROCESSED_DIR, name)
            if not os.path.isdir(path):
                continue
            log_path = os.path.join(path, "processing_log.json")
            summary = {}
            finished = ""
            if os.path.exists(log_path):
                try:
                    with open(log_path, encoding="utf-8") as handle:
                        summary = json.load(handle)
                    finished = summary.get("finished", "")
                except (ValueError, OSError):
                    summary = {}
            runs.append({
                "run_id": name,
                "path": path,
                "files": len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]),
                "finished_at": finished,
                "summary": summary,
                "counts": "training {0} rows · cut-offs {1} · scan review {2}".format(
                    summary.get("training", {}).get("rows_out", "?"),
                    summary.get("pdf_extraction", {}).get("cutoff_rows", "?"),
                    summary.get("pdf_extraction", {}).get("needs_review", "?")),
            })
    return runs


@admin_bp.route("/data")
@admin_required
def data_overview():
    runs = _list_runs()
    latest = runs[0] if runs else None
    quality = []
    if latest:
        quality_path = os.path.join(latest["path"], "uniguide_data_quality_report.csv")
        if os.path.exists(quality_path):
            import csv
            with open(quality_path, newline="", encoding="utf-8") as handle:
                quality = list(csv.DictReader(handle))
    inventory = []
    if os.path.exists(INVENTORY_CSV):
        import csv
        with open(INVENTORY_CSV, newline="", encoding="utf-8") as handle:
            inventory = list(csv.DictReader(handle))
    uploads = DatasetUpload.query.order_by(DatasetUpload.uploaded_at.desc()).limit(20).all()
    db_runs = DatasetRun.query.order_by(DatasetRun.created_at.desc()).limit(10).all()
    return render_template("admin/data.html", runs=runs, latest=latest, quality=quality,
                           inventory=inventory, uploads=uploads, db_runs=db_runs)


@admin_bp.route("/data/run", methods=["POST"])
@admin_required
def data_run():
    from datapipeline import pipeline as dp_pipeline

    try:
        result = dp_pipeline.run_pipeline()
    except Exception as exc:  # noqa: BLE001
        flash("Pipeline failed: {0}".format(exc), "error")
        return redirect(url_for("admin.data_overview"))

    output_dir = result["output_dir"] if isinstance(result, dict) else result
    run_id = os.path.basename(output_dir)
    summary = {}
    log_path = os.path.join(output_dir, "processing_log.json")
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as handle:
            summary = json.load(handle)
    db.session.add(DatasetRun(run_id=run_id, output_dir=output_dir, status="finished",
                              summary=json.dumps(summary), created_by=current_user.id))
    db.session.commit()
    log_activity("import", "dataset_run", None, {"run_id": run_id})
    flash("Pipeline run complete: {0}".format(run_id), "success")
    return redirect(url_for("admin.data_overview"))


@admin_bp.route("/data/upload", methods=["POST"])
@admin_required
def data_upload():
    from datapipeline import ingest

    upload = request.files.get("dataset")
    if upload is None or upload.filename == "":
        flash("Choose a file to upload.", "error")
        return redirect(url_for("admin.data_overview"))

    data = upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        flash("File is too large. Maximum upload size is 25 MB.", "error")
        return redirect(url_for("admin.data_overview"))
    try:
        stored_name = ingest.validate_upload(upload.filename, len(data), ingest.ALLOWED_TABULAR | ingest.ALLOWED_PDF)
    except ingest.IngestError as exc:
        flash("Upload rejected: {0}".format(exc), "error")
        return redirect(url_for("admin.data_overview"))

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    target = os.path.join(UPLOAD_DIR, stored_name)
    with open(target, "wb") as handle:
        handle.write(data)

    record = DatasetUpload(filename=upload.filename, stored_name=stored_name,
                           filetype=os.path.splitext(stored_name)[1].lower(),
                           size_bytes=len(data), status="stored",
                           notes="Stored in data/uploads/ for review before merging.",
                           uploaded_by=current_user.id)
    db.session.add(record)
    db.session.commit()
    log_activity("import", "dataset_upload", record.id,
                 {"filename": upload.filename, "size": len(data)})
    flash("Uploaded '{0}' ({1} bytes). Use Preview to check it before merging, then re-run "
          "the pipeline.".format(upload.filename, len(data)), "success")
    return redirect(url_for("admin.data_overview"))


@admin_bp.route("/data/download/<run_id>/<path:filename>")
@admin_required
def data_download(run_id, filename):
    if not run_id.replace("-", "").isalnum():
        abort(404)
    path = os.path.join(PROCESSED_DIR, run_id, filename)
    path = os.path.abspath(path)
    if not path.startswith(os.path.abspath(PROCESSED_DIR)) or not os.path.isfile(path):
        abort(404)
    return send_file(path, as_attachment=True)


def _preview_rows(path, limit=25):
    """Read the first rows of an uploaded CSV/Excel file for pre-import review."""
    import csv as csv_mod

    extension = os.path.splitext(path)[1].lower()
    rows, header, errors = [], [], []
    if extension == ".csv":
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as handle:
            reader = csv_mod.reader(handle)
            for index, row in enumerate(reader):
                if index == 0:
                    header = row
                else:
                    rows.append(row)
                if len(rows) >= limit:
                    break
    elif extension in (".xlsx", ".xls"):
        try:
            import openpyxl

            workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
            sheet = workbook.worksheets[0]
            for index, row in enumerate(sheet.iter_rows(values_only=True)):
                values = ["" if value is None else str(value) for value in row]
                if index == 0:
                    header = values
                else:
                    rows.append(values)
                if len(rows) >= limit:
                    break
            workbook.close()
        except Exception as exc:  # noqa: BLE001
            errors.append("Could not read the spreadsheet: {0}".format(exc))
    else:
        errors.append("Only CSV and Excel files can be previewed.")
    return header, rows, errors


def _duplicate_report(header, rows):
    """Flag rows whose University+Course already exist, plus in-file duplicates."""
    if "University" not in header or "Course" not in header:
        return [], len(rows), 0
    try:
        university_col = header.index("University")
        course_col = header.index("Course")
    except ValueError:
        return [], len(rows), 0
    existing = set()
    for university, name in db.session.query(University.name, Programme.name).join(
            Programme, Programme.university_id == University.id).all():
        existing.add((university.strip().lower(), name.strip().lower()))
    flagged, seen, invalid = [], set(), 0
    for index, row in enumerate(rows, start=1):
        if len(row) <= max(university_col, course_col):
            invalid += 1
            continue
        key = (row[university_col].strip().lower(), row[course_col].strip().lower())
        if not key[0] or not key[1]:
            invalid += 1
            continue
        if key in seen:
            flagged.append({"row": index, "reason": "duplicate inside this file",
                            "label": "{0} — {1}".format(row[university_col], row[course_col])})
        elif key in existing:
            flagged.append({"row": index, "reason": "already in the database",
                            "label": "{0} — {1}".format(row[university_col], row[course_col])})
        seen.add(key)
    return flagged, len(rows), invalid


@admin_bp.route("/data/uploads/<int:upload_id>/preview")
@admin_required
def data_preview(upload_id):
    record = db.session.get(DatasetUpload, upload_id)
    if record is None:
        abort(404)
    path = os.path.join(UPLOAD_DIR, os.path.basename(record.stored_name))
    if not os.path.isfile(path):
        flash("The stored file is no longer on disk.", "error")
        return redirect(url_for("admin.data_overview"))
    header, rows, errors = _preview_rows(path)
    flagged, total, invalid = _duplicate_report(header, rows)
    return render_template("admin/data_preview.html", record=record, header=header,
                           rows=rows, flagged=flagged, total=total, invalid=invalid,
                           errors=errors)


@admin_bp.route("/data/uploads/<int:upload_id>/delete", methods=["POST"])
@admin_required
def data_upload_delete(upload_id):
    record = db.session.get(DatasetUpload, upload_id)
    if record is None:
        abort(404)
    if not _require_confirm(record.filename):
        return redirect(url_for("admin.data_overview"))
    path = os.path.join(UPLOAD_DIR, os.path.basename(record.stored_name))
    try:
        db.session.delete(record)
        db.session.commit()
        if os.path.isfile(path) and os.path.abspath(path).startswith(os.path.abspath(UPLOAD_DIR)):
            try:
                os.remove(path)
            except OSError:
                pass
        log_activity("delete", "dataset_upload", upload_id, {"filename": record.filename})
        flash("Upload '{0}' removed.".format(record.filename), "info")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash("Could not delete the upload: {0}".format(exc), "error")
    return redirect(url_for("admin.data_overview"))


@admin_bp.route("/data/runs/<int:run_id>/delete", methods=["POST"])
@admin_required
def data_run_delete(run_id):
    record = db.session.get(DatasetRun, run_id)
    if record is None:
        abort(404)
    if not _require_confirm(record.run_id):
        return redirect(url_for("admin.data_overview"))
    try:
        db.session.delete(record)
        db.session.commit()
        log_activity("delete", "dataset_run", run_id, {"run_id": record.run_id})
        flash("Run record '{0}' removed. Files in data/processed/ were left "
              "unchanged.".format(record.run_id), "info")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash("Could not delete the run record: {0}".format(exc), "error")
    return redirect(url_for("admin.data_overview"))


@admin_bp.route("/export/<kind>")
@admin_required
def export_csv(kind):
    import csv as csv_mod
    import io

    from flask import Response

    if kind == "universities":
        rows = University.query.order_by(University.name).all()
        header = ["id", "name", "institution_type", "region", "district", "location",
                  "website", "application_link", "image", "active"]
        records = [[getattr(row, key) for key in header] for row in rows]
    elif kind == "programmes":
        rows = Programme.query.order_by(Programme.name).all()
        header = ["id", "university_id", "name", "level", "qualification_level",
                  "duration_years", "principal_passes", "essential_subjects",
                  "minimum_grades", "cutoff_government", "cutoff_private",
                  "tuition_government", "tuition_private", "admission_year",
                  "official_source", "active"]
        records = [[getattr(row, key) for key in header] for row in rows]
    elif kind == "careers":
        rows = Career.query.order_by(Career.name).all()
        header = ["id", "name", "description", "required_subjects", "skills", "pathways"]
        records = [[getattr(row, key) for key in header] for row in rows]
    else:
        abort(404)

    buffer = io.StringIO()
    writer = csv_mod.writer(buffer)
    writer.writerow(header)
    writer.writerows(records)
    log_activity("export", kind, None, {"rows": len(records)})
    return Response(buffer.getvalue(), mimetype="text/csv", headers={
        "Content-Disposition": "attachment; filename=uniguide_{0}.csv".format(kind),
    })


@admin_bp.route("/models")
@admin_required
def models_overview():
    from ml import predict as ml_predict

    try:
        artifacts = ml_predict.list_models()
    except Exception:  # noqa: BLE001
        artifacts = []
    versions = ModelVersion.query.order_by(ModelVersion.created_at.desc()).all()
    return render_template("admin/models.html", artifacts=artifacts, versions=versions)


@admin_bp.route("/models/train", methods=["POST"])
@admin_required
def models_train():
    from ml import train as ml_train

    try:
        results = ml_train.train_all()
    except Exception as exc:  # noqa: BLE001
        flash("Training failed: {0}".format(exc), "error")
        return redirect(url_for("admin.models_overview"))

    clf = results["discipline_classifier"]
    rec = results["content_recommender"]
    db.session.add(ModelVersion(
        name="programme_discipline_classifier", algorithm=clf["best_model_name"],
        artifact=os.path.basename(clf["model_path"]), target="discipline",
        feature_list=json.dumps(["programme text", "institution", "qualification_level", "institution_type"]),
        metrics=json.dumps(clf["metrics"]),
        limitations="Trained on NCHE discipline labels only. No admission-outcome labels exist in the data.",
        source_dataset="uniguide_training_dataset.csv", created_by=current_user.id))
    db.session.add(ModelVersion(
        name="content_based_recommender", algorithm="tfidf_cosine",
        artifact=os.path.basename(rec["model_path"]), target="programme_similarity",
        feature_list=json.dumps(["programme + institution text"]),
        metrics=json.dumps(rec["metrics"]),
        limitations="Evaluation uses careers.csv links as a weak, self-referential proxy, not held-out truth.",
        source_dataset="uniguide_nche_register_clean.csv", created_by=current_user.id))
    db.session.commit()
    flash("Training complete. Discipline macro-F1 = {0:.3f}, accuracy = {1:.3f}.".format(
        clf["metrics"]["macro_f1"], clf["metrics"]["accuracy"]), "success")
    return redirect(url_for("admin.models_overview"))


@admin_bp.route("/models/<int:version_id>/approve", methods=["POST"])
@admin_required
def model_approve(version_id):
    version = db.session.get(ModelVersion, version_id)
    if version is None:
        abort(404)
    version.approved = not version.approved
    db.session.commit()
    flash("{0} {1}.".format(version.name, "approved" if version.approved else "unapproved"), "info")
    return redirect(url_for("admin.models_overview"))


@admin_bp.route("/predict", methods=["GET", "POST"])
@admin_required
def predict():
    from ml import predict as ml_predict

    result = None
    recommendation = None
    form = {"programme": "", "institution": "", "qualification_level": "Bachelor", "institution_type": "University"}
    if request.method == "POST":
        form = {
            "programme": request.form.get("programme", "").strip(),
            "institution": request.form.get("institution", "").strip(),
            "qualification_level": request.form.get("qualification_level", "").strip(),
            "institution_type": request.form.get("institution_type", "").strip(),
        }
        if form["programme"]:
            result = ml_predict.predict_discipline(**form)
            recommendation = ml_predict.recommend_similar(form["programme"], top_k=5)
            db.session.add(PredictionLog(
                user_id=current_user.id, kind="discipline+similar",
                input_summary=json.dumps(form),
                output_summary=json.dumps({"discipline": result.get("predicted_discipline"),
                                           "similar": [i["programme"] for i in recommendation.get("items", [])]}),
                model_version=result.get("trained_at", "")))
            db.session.commit()
        else:
            flash("Enter a programme name.", "error")
    logs = PredictionLog.query.order_by(PredictionLog.created_at.desc()).limit(10).all()
    return render_template("admin/predict.html", result=result, recommendation=recommendation,
                           form=form, logs=logs)
