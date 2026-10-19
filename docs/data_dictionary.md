# Data Dictionary

## programmes.csv

Stored in the `Programme` table. Columns:

| Column | Type | Description |
|--------|------|-------------|
| University | text | University name (must match `universities.csv`). |
| Course | text | Official programme name. |
| Qualification Level | text | Entry qualification, e.g. `UACE`. |
| Essential Subjects | text | Semicolon-separated required A-Level subjects (scored ×3). |
| Minimum Grades | text | Semicolon-separated `Subject:Grade` minimums, e.g. `Biology:C;Chemistry:C`. |
| Principal Passes | text | Number of A-Level principal passes required. |
| Cut-off Points | text | `Gov:<n>;Private:<n>` weighted cut-off scores, or `NA`. |
| Tuition Fees | text | `Gov:<UGX>;Private:<UGX>` per academic year, or `NA`. |
| Academic Year | text | Admission year, e.g. `2026/27`. |
| Official Source | text | URL of the official document used. |
| Sponsorship | text | `Gov/Private`, `Private`, or `Gov`. |
| Citizenship Applicability | text | `Ugandan & Foreign` or `Ugandan`. |
| Required UCE | text | O-Level (UCE) requirement summary. |
| Subject Weights | text | Weighting scheme description. |
| Duration | int | Programme length in years. |
| District/Region | text | `Region/District` of the campus. |
| Application Link | text | Official application URL. |
| Data-Year | text | Year the data refers to. |

## universities.csv — stored in `University`

`name, institution_type (public/private), region, district, location, established, website, application_link, active`

## careers.csv — stored in `Career`, linked to programmes via `programme_careers`

`name, description, required_subjects, skills, pathways, programmes`

`programmes` is a semicolon-separated list of course name tokens used to link careers to programmes during seeding.

## Database tables (SQLite, `uniguide.db`)

- `users` — Student/Admin accounts (hashed passwords).
- `universities`, `programmes`, `careers`, `programme_careers`.
- `student_profiles` — academic results and preferences (JSON subject maps for flexibility).
- `saved_recommendations` — saved matches.
- `comparisons` — comparison history.
- `notifications` — per-student update alerts.

## Scoring model

- UACE grade points: A=6, B=5, C=4, D=3, E=2, F=1.
- Principal weight: essential ×3, relevant ×2, other ×1.
- Subsidiary (General Paper / Sub-Mathematics / ICT): ×0.5.
- A principal pass = grade A, B or C.