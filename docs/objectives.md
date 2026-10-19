# Objectives

## Functional objectives
1. Register and log in student and administrator accounts.
2. Capture a student profile: UCE summary, UACE subjects and grades, subsidiary subjects, budget,
   preferred region, preferred field, career interests and sponsorship preference.
3. Switch qualification handling between **Ugandan** students (UACE model) and **foreigners**
   (IGCSE/IB/WAEC/KCSE totals, NCHE minimums).
4. Recommend courses grouped by status: **Eligible**, **Borderline**, **Not eligible**.
5. Show, for every recommendation: university, course, location, tuition, duration, entry requirements,
   suitability score, reasons, missing requirements, admission year, and official application link.
6. Recommend A-Level subject combinations for a chosen field or career interests.
7. Compare two or more universities side by side, with comparison history.
8. Provide an AI guidance chatbot grounded in the verified dataset.
9. Export recommendations as a PDF report.
10. Admin dashboard to add/edit/delete universities, programmes and careers, and re-import the dataset.

## Non-functional objectives
- **Usability:** mobile, tablet and desktop responsive; consistent navigation; accessible forms.
- **Reliability:** data seeded from auditable CSV sources with an official-source column.
- **Performance:** page loads render in well under a second for a 30-programme dataset.
- **Security:** hashed passwords, session-based auth, role-based access, minimal data collection.
- **Maintainability:** blueprints, model layer, and a data-driven engine so new admissions data
  can be dropped in without code changes.

## Evaluation metrics
- % of recommended "Eligible" programmes that actually satisfy the student's stated constraints
  (see `evaluation_report.md`).
- Test coverage of the engine and routes (35 automated tests).
- Breadth of the dataset (universities, programmes, careers, official sources).