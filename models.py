import json
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)

from flask_login import UserMixin

from extensions import db


def jsonify(value):
    return json.dumps(value)


def parse_json(value, fallback=None):
    if not value:
        return fallback if fallback is not None else {}
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return fallback if fallback is not None else {}


programme_careers = db.Table(
    "programme_careers",
    db.Column("programme_id", db.Integer, db.ForeignKey("programmes.id"), primary_key=True),
    db.Column("career_id", db.Integer, db.ForeignKey("careers.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student", nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    profile = db.relationship("StudentProfile", backref="user", uselist=False)
    saved = db.relationship("SavedRecommendation", backref="user", lazy="dynamic")
    comparisons = db.relationship("ComparisonHistory", backref="user", lazy="dynamic")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic")

    def is_admin(self):
        return self.role == "admin"

    @property
    def is_active(self):
        return self.active is not False


class University(db.Model):
    __tablename__ = "universities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    institution_type = db.Column(db.String(30), default="public")
    region = db.Column(db.String(80))
    district = db.Column(db.String(80))
    location = db.Column(db.String(120))
    established = db.Column(db.Integer)
    website = db.Column(db.String(255))
    application_link = db.Column(db.String(255))
    image = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    programmes = db.relationship("Programme", backref="university", lazy="dynamic")

    def initials(self):
        parts = [p for p in self.name.split() if p]
        return "".join(p[0].upper() for p in parts[:3])


class Programme(db.Model):
    __tablename__ = "programmes"

    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey("universities.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    level = db.Column(db.String(30), default="Bachelor")
    qualification_level = db.Column(db.String(40), default="UACE")
    duration_years = db.Column(db.Integer, default=3)
    essential_subjects = db.Column(db.String(255))
    relevant_subjects = db.Column(db.String(255))
    minimum_grades = db.Column(db.String(255))
    principal_passes = db.Column(db.Integer, default=2)
    uce_requirement = db.Column(db.String(255))
    cutoff_government = db.Column(db.Integer)
    cutoff_private = db.Column(db.Integer)
    foreign_min_total = db.Column(db.Integer)
    tuition_government = db.Column(db.Integer)
    tuition_private = db.Column(db.Integer)
    international_eligible = db.Column(db.Boolean, default=True)
    admission_year = db.Column(db.String(20), default="2026/27")
    official_source = db.Column(db.String(255))
    fees_verified = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    careers = db.relationship("Career", secondary=programme_careers, backref=db.backref("programmes", lazy="dynamic"))

    def essential_list(self):
        return split_field(self.essential_subjects)

    def relevant_list(self):
        return split_field(self.relevant_subjects)


class Career(db.Model):
    __tablename__ = "careers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    required_subjects = db.Column(db.String(255))
    skills = db.Column(db.String(255))
    pathways = db.Column(db.String(255))


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    citizenship = db.Column(db.String(20), default="ugandan")
    uace_subjects = db.Column(db.Text)
    uace_subsidiary = db.Column(db.Text)
    uce_summary = db.Column(db.String(255))
    foreign_qual = db.Column(db.Text)
    preferred_field = db.Column(db.String(80))
    career_interests = db.Column(db.Text)
    budget = db.Column(db.Integer)
    preferred_region = db.Column(db.String(80))
    sponsorship_pref = db.Column(db.String(20), default="private")
    gender = db.Column(db.String(20))
    sports_level = db.Column(db.String(30))
    sports_details = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def subjects(self):
        return parse_json(self.uace_subjects, {})

    def subsidiary(self):
        return parse_json(self.uace_subsidiary, {})

    def interests(self):
        return parse_json(self.career_interests, [])

    def foreign(self):
        return parse_json(self.foreign_qual, {})

    @property
    def data(self):
        return self.to_dict()

    def to_dict(self):
        return {
            "citizenship": self.citizenship,
            "uace_subjects": self.subjects(),
            "uace_subsidiary": self.subsidiary(),
            "uce_summary": self.uce_summary or "",
            "foreign": self.foreign(),
            "preferred_field": self.preferred_field or "",
            "career_interests": self.interests(),
            "budget": int(self.budget) if self.budget else None,
            "preferred_region": self.preferred_region or "",
            "sponsorship_pref": self.sponsorship_pref or "private",
            "gender": self.gender or "",
            "sports_level": self.sports_level or "",
            "sports_details": self.sports_details or "",
        }


class SavedRecommendation(db.Model):
    __tablename__ = "saved_recommendations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    programme_id = db.Column(db.Integer, db.ForeignKey("programmes.id"), nullable=False)
    status = db.Column(db.String(20))
    suitability = db.Column(db.Integer, default=0)
    score = db.Column(db.Float)
    saved_at = db.Column(db.DateTime, default=utcnow)

    programme = db.relationship("Programme")


class ComparisonHistory(db.Model):
    __tablename__ = "comparisons"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    university_ids = db.Column(db.Text)
    programme_ids = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)

    def uni_ids(self):
        return parse_json(self.university_ids, [])

    def prog_ids(self):
        return parse_json(self.programme_ids, [])


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.String(300))
    link = db.Column(db.String(255))
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class Enquiry(db.Model):
    __tablename__ = "enquiries"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), default="Other Enquiries")
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class DatasetUpload(db.Model):
    __tablename__ = "dataset_uploads"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    filetype = db.Column(db.String(20))
    size_bytes = db.Column(db.Integer)
    status = db.Column(db.String(30), default="stored")
    notes = db.Column(db.String(255))
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=utcnow)


class DatasetRun(db.Model):
    __tablename__ = "dataset_runs"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(40), nullable=False, index=True)
    output_dir = db.Column(db.String(255))
    status = db.Column(db.String(30), default="finished")
    summary = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow)

    def summary_dict(self):
        return parse_json(self.summary, {})


class ModelVersion(db.Model):
    __tablename__ = "model_versions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    algorithm = db.Column(db.String(80))
    artifact = db.Column(db.String(255), nullable=False)
    target = db.Column(db.String(80))
    feature_list = db.Column(db.Text)
    metrics = db.Column(db.Text)
    limitations = db.Column(db.Text)
    source_dataset = db.Column(db.String(80))
    approved = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow)

    def metrics_dict(self):
        return parse_json(self.metrics, {})

    def features(self):
        return parse_json(self.feature_list, [])


class PredictionLog(db.Model):
    __tablename__ = "prediction_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    kind = db.Column(db.String(40))
    input_summary = db.Column(db.Text)
    output_summary = db.Column(db.Text)
    model_version = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=utcnow)


DEFAULT_SETTINGS = {
    # General
    "site_name": "UniGuide Uganda",
    "site_description": "AI-powered university and course recommendation system for students in Uganda.",
    "contact_email": "kasumbakevin123@gmail.com",
    "contact_phone": "+256 751 761 977",
    "homepage_image": "campus-hero.jfif",
    "items_per_page": "10",
    "date_format": "%d %B %Y",
    # University / programme defaults
    "default_admission_year": "2026/27",
    "preference_fields": "Computing & IT,Engineering,Medicine & Health,Business & Management,"
                          "Education,Law,Sciences,Arts & Humanities,Agriculture",
    "programmes_active_by_default": "1",
    # Recommendation engine (scoring only - never overrides hard admission rules)
    "weight_essential": "3",
    "weight_relevant": "2",
    "weight_other": "1",
    "weight_subsidiary": "0.5",
    "use_budget_match": "1",
    "use_region_match": "1",
    "use_career_match": "1",
    "use_fee_preference": "1",
    "budget_tolerance_pct": "30",
    # Appearance
    "theme": "light",
    "accent_color": "#1B7F5A",
    "show_university_logos": "1",
    "sidebar_compact": "0",
    "homepage_title": "",
}


class Setting(db.Model):
    """Key/value application settings managed from the admin portal."""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)
    group = db.Column(db.String(40), default="general")
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    @staticmethod
    def get(key, default=None):
        if default is None:
            default = DEFAULT_SETTINGS.get(key, "")
        row = Setting.query.filter_by(key=key).first()
        if row is None or row.value is None or row.value == "":
            return default
        return row.value

    @staticmethod
    def get_bool(key, default=None):
        return str(Setting.get(key, default)) in ("1", "true", "True", "on", "yes")

    @staticmethod
    def get_int(key, default=0):
        try:
            return int(float(Setting.get(key, str(default))))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def set(key, value, group="general", user_id=None):
        row = Setting.query.filter_by(key=key).first()
        if row is None:
            row = Setting(key=key, group=group)
            db.session.add(row)
        row.value = "" if value is None else str(value)
        row.group = group
        row.updated_by = user_id
        return row

    @staticmethod
    def ensure_defaults(user_id=None):
        for key, value in DEFAULT_SETTINGS.items():
            if Setting.query.filter_by(key=key).first() is None:
                db.session.add(Setting(key=key, value=value, updated_by=user_id))


class ActivityLog(db.Model):
    """Administrator activity trail. Never stores passwords or tokens."""

    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(30), nullable=False, index=True)
    entity = db.Column(db.String(40), index=True)
    entity_id = db.Column(db.Integer)
    detail = db.Column(db.Text)
    ip = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=utcnow, index=True)

    user = db.relationship("User", foreign_keys=[user_id])

    def detail_dict(self):
        return parse_json(self.detail, {})

    def summary(self):
        data = self.detail_dict()
        label = (data.get("name") or data.get("title") or data.get("filename")
                 or ("#{0}".format(self.entity_id) if self.entity_id else ""))
        verb = {
            "create": "created",
            "update": "updated",
            "delete": "deleted",
            "deactivate": "deactivated",
            "activate": "activated",
            "import": "ran an import of",
            "login": "logged in",
            "login_failed": "failed to log in",
            "password_change": "changed a password",
            "setting": "updated settings",
        }.get(self.action, self.action)
        return "{0} {1} {2}".format(verb, self.entity or "", label).strip()


def split_field(value):
    if not value:
        return []
    return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]