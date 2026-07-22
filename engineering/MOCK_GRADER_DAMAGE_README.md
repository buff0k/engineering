# Mock grader utilisation vs mock tyre damage

This development-only dataset is isolated from actual Availability and
Utilisation records.

- Mock grader utilisation is stored in `mock_grader_utilisation.json`.
- Mock damage is written only to draft Tyre Surveys whose inspector is
  `Mock Survey Generator`.
- Every seeded damage note contains
  `[MOCK DAMAGE: GRADER-COMPARISON-2026]`.
- Run `engineering.seed_mock_tyre_damage.seed` in dry-run mode before apply.
