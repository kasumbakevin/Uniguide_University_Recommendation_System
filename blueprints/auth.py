from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, login_manager
from models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        errors = []
        if not name:
            errors.append("Please provide your full name.")
        if "@" not in email or "." not in email:
            errors.append("Please provide a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter_by(email=email).first() is not None:
            errors.append("An account with this email already exists.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("auth/register.html", name=name, email=email)

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role="student",
        )
        db.session.add(user)
        db.session.commit()

        from flask_login import login_user

        login_user(user)
        flash("Account created. Welcome to UniGuide Uganda!", "success")
        return redirect(url_for("student.profile"))

    return render_template("auth/register.html", name="", email="")


@auth_bp.route("/auth/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=identifier.lower()).first()
        if user is None:
            user = User.query.filter_by(username=identifier.lower()).first()
        if user is None or not check_password_hash(user.password_hash, password):
            from activity import log_activity

            log_activity("login_failed", "user", user.id if user else None,
                         {"identifier": identifier[:120]})
            flash("Invalid email/username or password.", "error")
            return render_template("auth/login.html", email=identifier)
        if user.active is False:
            from activity import log_activity

            log_activity("login_failed", "user", user.id, {"identifier": identifier[:120],
                                                           "reason": "account deactivated"})
            flash("This account has been deactivated. Contact the administrator.", "error")
            return render_template("auth/login.html", email=identifier)

        from flask_login import login_user

        login_user(user)
        from activity import log_activity

        log_activity("login", "user", user.id, {"identifier": identifier[:120]})
        flash("Welcome back, {0}!".format(user.name), "success")
        if user.is_admin():
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("student.dashboard"))

    return render_template("auth/login.html", email="")


@auth_bp.route("/auth/logout")
def logout():
    from flask_login import logout_user

    from activity import log_activity

    admin_id = current_user.id if (current_user.is_authenticated and current_user.is_admin()) else None
    logout_user()
    if admin_id is not None:
        log_activity("logout", "user", admin_id)
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))