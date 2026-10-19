# Requirements Specification

## Functional requirements

### User registration and authentication
- FR-01 Students can register with name, email, password.
- FR-02 Passwords are hashed; sessions protect protected pages.
- FR-03 Administrators have a distinct role with restricted admin pages.
- FR-04 Users can log out and log back in.

### Student profile
- FR-05 Capture citizenship (Ugandan / Foreigner) via a dropdown that changes the form fields.
- FR-06 Ugandan: up to 3 principal subjects with grades, General Paper and Sub-Mathematics optional,
      UCE summary.
- FR-07 Foreign: qualification type, total score, optional subject list.
- FR-08 Preferences: preferred field, career interests, annual budget, preferred region,
      sponsorship preference (government/private).
- FR-09 Profile persists and can be edited.

### Recommendation engine
- FR-10 Compute weighted score (essential ×3, relevant ×2, other ×1, subsidiary ×0.5).
- FR-11 Check principal passes, essential subjects and minimum grades.
- FR-12 Compare weighted score against government and private cut-offs.
- FR-13 Classify as Eligible / Borderline / Not eligible with reasons and missing requirements.
- FR-14 Foreign students matched against programme qualification minimums and international eligibility.
- FR-15 Rank results by status then suitability (score margin, budget fit, region fit).
- FR-16 Filter results by preferred field/keywords.
- FR-17 Show admission year and official source with every result.

### Subject and career guidance
- FR-18 Suggest A-Level subject combinations for a field or set of interests.
- FR-19 Show careers linked to each recommended programme.

### Comparison
- FR-20 Select two or more universities and compare programmes, fees, cut-offs, location, entry.
- FR-21 Store comparison history per student.

### AI guidance chatbot
- FR-22 Answer questions about courses, cut-offs, fees, and careers using the verified dataset.
- FR-23 Direct students to confirm eligibility with university international offices where relevant.

### Reports
- FR-24 Printable HTML report and downloadable PDF (ReportLab).

### Admin
- FR-25 CRUD for universities, programmes, careers.
- FR-26 Re-import the full dataset from `data/*.csv`.
- FR-27 View registered users and usage statistics.
- FR-28 Notify students when programme information is updated.

## Non-functional requirements
- NFR-01 Usable on smartphones, tablets and desktop (responsive CSS).
- NFR-02 Consistent theme (white, light grey, navy #12345A, green #18794E, gold #F4B942).
- NFR-03 Private data (grades, budget) stored locally and collected minimally.
- NFR-04 Dataset rows carry official-source URLs for auditability.
- NFR-05 Works offline as a local application; no external assets required.