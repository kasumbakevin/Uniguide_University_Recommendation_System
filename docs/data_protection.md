# Data Protection Policy

## Principles
UniGuide Uganda collects only the personal data needed to provide recommendations:

- name and email (account)
- academic results (subjects, grades, UCE summary, qualification totals)
- advice-related preferences (budget, region, field, sponsorship, careers)

## Processing
- Data is stored in a local SQLite database (`uniguide.db`) on the hosting machine.
- Passwords are hashed (Werkzeug). Plain-text passwords are never stored.
- Recommendations are generated from this data and the public, officially-sourced admission dataset.
- PDF reports contain metadata about the export time and student, used only for the report itself.

## Retention
- Accounts may be deleted by the developer via the admin layer; all linked saved recommendations,
  comparisons, profiles and notifications are removed with the account.
- Session cookies are cleared on logout.

## Sharing
- Personal data is never sold or shared. The only "sharing" is the PDF the student downloads themselves.

## Access controls
- Students can only read their own profile, saved items and history.
- Admin accounts can manage content and view aggregate statistics.
- Admin routes reject student sessions (403).

## Ugandan context
- Handled under the Data Protection and Privacy Act 2019 (DPPA) and general good practice:
  lawfulness, purpose-limitation, data-minimisation, accuracy, storage limitation, integrity,
  and accountability.

## Risks and mitigations
- Demo credentials in `seed.py` must be changed before any public deployment.
- Removed: nothing stored in localStorage; no external analytics; no third-party cookies.