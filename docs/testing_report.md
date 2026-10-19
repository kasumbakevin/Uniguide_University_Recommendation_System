# Testing Report

Tooling: `pytest`. Run with `python -m pytest tests -q`.

## Test scope

| Area | File | Number of tests |
|------|------|-----------------|
| Recommendation engine | `tests/test_engine.py` | 11 |
| Routes / workflows | `tests/test_routes.py` | 15 |
| Dataset integrity | `tests/test_data.py` | 9 |

**Result: 35 passed, 0 failures.**

## Engine tests (highlights)
- Subject-name normalisation (`Mathematics` ≡ `maths`, `CS` ≡ `Computer Science`, `GP` ≡ `General Paper`).
- Weighted score arithmetic (essential/relevant/other/subsidiary weights).
- Principal-pass counting (A–C).
- Eligibility outcomes: Eligible, Borderline (score within 2 below cut-off), Not eligible (missing essential
  subject, below minimums).
- Foreign path: Eligible above qualification minimum, Not eligible below minimum.
- `analyse_one` output contract (all required fields present).
- Recommendation runs against the seeded database and honours the preferred-field filter
  (Computing results contain Software; Law results contain Laws).

## Route tests (highlights)
- Home, register, login, profile requires login.
- Ugandan profile submission (3 subjects + subsidiary) and foreign profile submission redirect correctly.
- Recommendations render after a profile is saved.
- Chatbot endpoint returns an answer.
- PDF report downloads with `application/pdf` content type.
- Public university detail page.
- Admin pages denied (403) for students; admin can open dashboard and add a programme, which is persisted.

## Data tests (highlights)
- Required spreadsheet columns exist: `University | Course | Qualification Level | Essential Subjects | Minimum
  Grades | Principal Passes | Cut-off Points | Tuition Fees | Academic Year | Official Source`.
- ≥20 programme rows; every university reference resolves; no duplicate (University, Course) pairs.
- Cut-off points and tuition values parse as numeric (`NA` allowed).
- Career file present with ≥10 careers and a `programmes` mapping column.

## Known issues / future work
- PDF formatting is basic table-based; consider vertical page headers for large exports.
- Notifications are generated on programme changes but not pushed externally.
- Chatbot is rule-based; an LLM retrieval layer could improve phrasing while keeping grounding (
  covered under "AI depth" in the plan).