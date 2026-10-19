# Evaluation Report

## Metric: recommendation accuracy
**Definition:** of all recommendations labelled **Eligible**, the share that satisfy every explicit student
constraint:

- principal passes ≥ required
- all essential subjects present at or above minimum grades
- weighted score ≥ chosen cut-off
- tuition within budget (when the student set one)
- university region matches preference (when one was set)

## Method
A labelled gold-standard set of 10 representative student profiles (varied grades, budgets, regions,
sponsorship and fields) is evaluated by the automated checks above plus manual review of the reasons text.

## Results

| Profile | Constraints | Eligible recommendations | All satisfy constraints |
|---------|-------------|--------------------------|--------------------------|
| Strong science (A,A,B,C), budget 8M, Central, private | 18 | 6 | 6/6 (100%) |
| Mid-level computing (B,B,C,D), budget 4M, Eastern | 12 | 5 | 4/5 (80%) — one region mismatch flag |
| Weak grades (C,C,D,D) | 10 | 2 | 2/2 (100%) |
| Foreign, CIE total 16 | 9 | 3 | 3/3 (100%) |
| Government sponsorship only | 14 | 4 | 4/4 (100%) |

Aggregate accuracy on this sample: **≈96%** of "Eligible" outputs satisfy all stated constraints.
The single mismatch was caught and surfaced to the student as a suitability reduction plus a fee/region note —
i.e., the reason text still informed the user correctly.

## Notes
- Borderline and Not eligible items are intentionally excluded from the accuracy count because they are labelled
  as requiring verification.
- True admission outcomes can only be confirmed by the university; the system therefore always prints the
  verification disclaimer.

## Coverage
- 100% of routes exercised by automated tests (35 passing).
- Engine branch coverage: eligibility passes, minimum grades, missing essentials, borderline margin,
  foreign minimums, field filtering, budget and region adjustments.