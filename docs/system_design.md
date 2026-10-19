# System Design

## Architecture
Three-tier web application:

- **Presentation:** Jinja2 templates + CSS/JS (single-page flows, mobile-first).
- **Application:** Flask blueprints (`main`, `auth`, `student`, `admin`) and the engine modules.
- **Data:** SQLite via SQLAlchemy ORM; canonical dataset in CSV under `data/`.

```
Browser ──> Flask (blueprints) ──> recommender/courses/chatbot ──> SQLAlchemy ──> SQLite
                                    │
                                    └── report.py (ReportLab PDF)
```

## Entity-relationship summary

```
User 1───1 StudentProfile
User 1───* SavedRecommendation / Comparison / Notification
University 1───* Programme
Career *───* Programme        (programme_careers junction)
```

## Recommendation pipeline

1. Load profile and preferences.
2. Optional pre-filter by preferred field keywords.
3. For each active programme compute a decision object:
   - Ugandan: passes check → essential/min-grade check → weighted score → cut-off comparison.
   - Foreign: international eligibility → total vs qualification minimum.
4. Build reason strings and missing-requirement list.
5. Compute suitability (0–100): status base + budget/region adjustments.
6. Sort by status order, then suitability, then score.
7. Render cards / PDF.

## Weighted scoring (Ugandan)

grade points A=6 … F=1; essential ×3, relevant ×2, other ×1; subsidiary ×0.5.

## Security design
- Password hashing: Werkzeug `generate_password_hash`.
- Auth: Flask-Login sessions; `@login_required` and custom `@admin_required`.
- CSRF disabled only in tests; enabled in production config.
- Role-based access: admin blueprints return 403 for students.
- Data minimisation per data-protection policy.

## API-like endpoints (client-side usage)
- `POST /chatbot/ask` → JSON `{ "answer": "..." }`.
- `GET /report/pdf` → PDF download.

## Deployment
- Local: `python app.py`.
- Hosted: `wsgi.py` exposes the app; run with gunicorn/waitress (Windows) and a reverse proxy.