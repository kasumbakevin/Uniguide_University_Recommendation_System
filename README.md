# UniGuide Uganda

AI-Powered University and Course Recommendation System for Students in Uganda.

Students enter their UCE/UACE results (or an international qualification), budget, preferred region and career
interests. UniGuide checks minimum admission requirements, compares essential subjects, fees and location, ranks
eligible universities and courses with clear reasons, and exports a PDF report.

## Quick start

Requires Python 3.10+ (tested on 3.14).

```
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Demo accounts

| Role    | Username | Email               | Password    |
|---------|----------|---------------------|-------------|
| Admin   | admin    | admin@uniguide.ug   | admin123    |
| Student | student  | student@uniguide.ug | student123  |

You can log in with either the username or the email address. Change these in `seed.py` before public
deployment.

## Project structure

```
university recommedation system/
├── app.py                  # Flask application factory
├── wsgi.py                 # Production entry point
├── config.py               # Configuration
├── extensions.py           # SQLAlchemy + LoginManager
├── models.py               # Database models
├── recommender.py          # Recommendation engine
├── courses.py              # A-Level subject combinations / fields
├── chatbot.py              # Rule-based AI career guidance
├── report.py               # PDF report generation (ReportLab)
├── seed.py                 # Seeds the database from data/ CSVs
├── blueprints/             # main, auth, student, admin routes
├── data/                   # Verified admission dataset (CSV)
│   ├── universities.csv
│   ├── programmes.csv
│   └── careers.csv
├── templates/              # Jinja2 templates
├── static/
│   ├── css/style.css       # UniGuide theme
│   └── js/app.js           # Citizenship dropdown, chat, mobile menu
├── tests/                  # pytest suite (35 tests)
└── docs/                   # Project documentation pack
```

## Dataset

The dataset follows the agreed spreadsheet schema:

`University | Course | Qualification Level | Essential Subjects | Minimum Grades | Principal Passes | Cut-off Points | Tuition Fees | Academic Year | Official Source`

plus operational columns. Every programme row cites an official source URL. The current dataset is a realistic
sample (10 universities, 31 programmes, 21 careers) built from official 2026/27 documents (Makerere cut-off points,
NCHE minimum entry regulations). Replace/extend the CSVs and use **Admin → Import dataset** to reseed
— no code changes required.

## How the recommendation engine works

1. Hard filter — principal passes, essential subjects, minimum grades (Ugandan) or qualification minimums (foreign).
2. Weighted score — essential subjects ×3, relevant ×2, other ×1, subsidiary ×0.5.
3. Rank — status (Eligible / Borderline / Not eligible), then suitability (score margin, budget fit, region fit).
4. Output — status, weighted score vs cut-off, reasons, missing requirements, admission year, official source and
   application link.

## Feature notes

- **Citizenship dropdown** switches the qualification model: UACE subjects/grades for Ugandan students, and
  qualification type + total for international students (NCHE minimums, international office route).
- **Admin dashboard** manages universities, programmes, careers and users, with CSV re-import.
- **AI Guide** is a rule-based chatbot grounded in the verified dataset; eligibility must always be confirmed with
  the university before applying.

## Testing

```
python -m pytest tests -q
```

## Security / data protection

Passwords are hashed with Werkzeug. Only necessary student data is collected. See `docs/data_protection.md`.