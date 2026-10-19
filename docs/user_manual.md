# User Manual

## Getting started
1. Run the app: `python app.py` in the project folder, open http://127.0.0.1:5000
2. Create a student account (Register) or use the demo accounts shown in the README.

## Student guide

### 1. Set up your profile (recommended before recommendations)
Go to **My Profile** and choose your citizenship from the dropdown:
- **Ugandan** — enter your UACE subjects and grades (e.g. Biology B, Chemistry B),
  optional General Paper / Sub-Mathematics, and any UCE notes.
- **Foreigner** — choose qualification type (CIE A-Level, IB, WAEC, KCSE, Other),
  enter your total score and optional subjects.

Then set your preferences: preferred field (Computing, Health, Engineering, Law, Business, Education, Science,
Agriculture/Environment), career interests, annual budget, preferred region, and sponsorship preference.
Save. You can return and update this at any time.

### 2. Get recommendations
Open **My Recommendations**. Results are grouped:
- **Eligible** — you meet all requirements.
- **Borderline** — your weighted score is within 2 points of the cut-off; you may have a chance.
- **Not eligible** — missing requirements are listed so you can see why, and what to improve.

Each card shows the university, course, location, duration, tuition (gov/private), cut-off points, entry
requirements, your weighted score, and the official admission year, source and application link.
Save any programme you like with **Save**.

### 3. Explore universities and courses
Use **Universities** to browse all institutions and their programmes. Use **Compare** to examine two or more
universities side by side, then view your comparison history.

### 4. Subject and career guidance
Use **AI Guide** to ask questions such as: *"What subjects do I need for Medicine?"*, *"Which courses suit me
for law careers?"*, or *"What is the cut-off for Software Engineering at Kyambogo?"*.
Browsing a course card shows its entry requirements and related careers.

### 5. Export your report
On the recommendations page, use **Export PDF** (or the standalone Report page) to download a printable PDF
of your results.

## Admin guide (admin@uniguide.ug)
- **Dashboard** — overview of students, universities, programmes and saved recommendations.
- **Universities / Programmes / Careers** — add, edit or delete records.
- **Import dataset** — upload the new `data/*.csv` sources to fully reseed the site for a new admission year.
- **Users** — review registered accounts.
- When a programme is updated, affected students get a notification on their dashboard.