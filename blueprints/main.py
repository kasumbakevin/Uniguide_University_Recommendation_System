from urllib.parse import quote

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from extensions import db
from models import Career, Enquiry, Programme, University

main_bp = Blueprint("main", __name__)

CONTACT_EMAIL = "kasumbakevin123@gmail.com"
WHATSAPP_NUMBER = "+256 751 761 977"
WHATSAPP_LINK = "https://wa.me/256751761977"
ENQUIRY_CATEGORIES = [
    "Admission Requirements",
    "University Recommendations",
    "Admission Points",
    "Tuition Fees",
    "Technical Support",
    "Other Enquiries",
]


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    email_error = None
    if request.method == "POST":
        name = (request.form.get("name", "") or "").strip()
        email = (request.form.get("email", "") or "").strip().lower()
        category = (request.form.get("category", "") or "").strip()
        subject = (request.form.get("subject", "") or "").strip()
        message = (request.form.get("message", "") or "").strip()

        if not name:
            email_error = "Please provide your full name."
        elif not email or "@" not in email or "." not in email:
            email_error = "Please provide a valid email address."
        elif category not in ENQUIRY_CATEGORIES:
            email_error = "Please choose an enquiry category."
        elif not message:
            email_error = "Please write a short message."
        else:
            db.session.add(Enquiry(
                name=name,
                email=email,
                category=category,
                subject=subject or "Enquiry from {0}".format(name),
                message=message,
            ))
            db.session.commit()
            body = "{0}\n\nCategory: {1}\nContact email: {2}\n\n{3}".format(
                message, category, email, name)
            mailto = "mailto:{0}?subject={1}&body={2}".format(
                CONTACT_EMAIL,
                quote(subject or "UniGuide Uganda enquiry"),
                quote(body),
            )
            flash("Your enquiry has been recorded. Your email app will now open so you can send it "
                  "to {0} — nothing has been sent automatically.".format(CONTACT_EMAIL), "success")
            return redirect(url_for("main.contact", mailto=mailto))

    return render_template(
        "contact.html",
        contact_email=CONTACT_EMAIL,
        whatsapp_number=WHATSAPP_NUMBER,
        whatsapp_link=WHATSAPP_LINK,
        categories=ENQUIRY_CATEGORIES,
        email_error=email_error,
        mailto=request.args.get("mailto", ""),
    )


@main_bp.route("/")
def index():
    universities = University.query.filter_by(active=True).order_by(University.name).all()
    programme_count = Programme.query.filter_by(active=True).count()
    career_count = Career.query.count()
    return render_template(
        "index.html",
        universities=universities,
        programme_count=programme_count,
        career_count=career_count,
    )


@main_bp.route("/universities")
def universities():
    items = University.query.filter_by(active=True).order_by(University.name).all()
    return render_template("universities.html", universities=items)


@main_bp.route("/university/<int:university_id>")
def university_detail(university_id):
    university = db.session.get(University, university_id)
    if university is None:
        abort(404)
    programmes = Programme.query.filter_by(university_id=university.id, active=True).all()
    return render_template("university.html", university=university, programmes=programmes)