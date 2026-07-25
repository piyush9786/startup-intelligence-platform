# Recommendations Engine (`v1` + ML Blend)

## Scope

The recommendation generator evaluates every active scheme whose current
version is verified. Each evaluation is persisted as an `EligibilityAssessment`.

Only assessments with the `eligible` result are candidates. The current
application status must be one of: `open`, `rolling`, or `unknown`.

---

## Scoring Architecture (SVM-Blended ML Ranking)

Recommendation scores blend deterministic rule evaluations with **Calibrated SVM Scheme Success Probability (Model 4)**:

```text
Score = eligibility_component (0.40)
      + rule_match_component (0.10)
      + svm_component (0.40)
      + application_status_component (0.10)
```

### Components:
1. **Eligibility Component**: Base value `0.400000` for eligible assessments.
2. **Rule Match Component**: Up to `0.100000` proportional to matched rule ratio.
3. **SVM Component**: `0.400000` × Calibrated SVM probability score ($0.0-1.0$) output by `apps.ml_engine.services.models.svm_ranker`.
4. **Application Status Component**: Up to `0.100000` based on status (`open` = `0.10`, `rolling` = `0.09`, `unknown` = `0.05`).

### Heuristic Fallback
If the SVM model artifact is not yet trained or unavailable, the system automatically falls back to the original deterministic score formula (`0.70` base + `0.20` rule match + `0.10` status).

---

## Ranking

Recommendations are ordered by:
1. `score` descending;
2. `canonical_name` case-insensitive;
3. `scheme_version_id` UUID.

Ranks start at 1 and are unique inside a recommendation generation run.

---

## Data Model & Audit Trail

Recommendation rows carry:
- `generation_id` & `ranking_version`
- `svm_score` (Calibrated SVM probability float)
- `ml_score_breakdown` (JSON breakdown of all 4 formula components)
- `evidence_snapshot` (Evidence rules metadata)

---

## API

`POST /api/v1/recommendations/generate/`

Authentication required. Returns ranked recommendations with `svm_score` and `ml_score_breakdown`.
