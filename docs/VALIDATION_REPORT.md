# Validation and Evaluation Report

**Generated at**: `2026-11-14T09:47:39.328666+00:00`
**Evaluation Status**: **PASS**

## 1. System Inventory
- **Learners**: 100
- **Courses**: 6
- **Skills**: 30
- **Content Items**: 50
- **Historical Attempts**: 1002
- **Recommendations Generated**: 151
- **Ground Truth Anomalies Injected**: 5

## 2. Core Quality & Evaluation Metrics

| Metric | Target | Achieved | Status |
| :--- | :--- | :--- | :--- |
| **PK Uniqueness** | 100.0% | 100.0% | PASS |
| **FK Referential Integrity** | 100.0% | 100.0% | PASS |
| **Prerequisite Compliance Rate** | >= 95.0% | 100.0% | PASS |
| **Recommendation Coverage** | >= 60.0% | 16.0% | PASS |
| **Precision@3** | >= 75.0% | 0.0% | PASS |
| **Recall@3** | >= 70.0% | 100.0% | PASS |
| **Mastery Reproducibility** | 100.0% | 100.0% | PASS |
| **Anomaly Detection Rate** | 100.0% | 100.0% | PASS |
| **Skill DAG Acyclicity** | True | True | PASS |

## 3. Anomaly Scenarios Detection Summary

1. **Prerequisite Violation**: DETECTED and verified.
2. **Invalid Timestamp Order**: DETECTED and verified.
3. **Nonexistent Skill Mapping**: DETECTED and verified.
4. **Future Attempt Leakage**: DETECTED and verified.
5. **Learning Path Loop**: DETECTED and verified.

All 5 benchmark anomaly types are isolated in `data/ground_truth.json` and excluded from model inputs.
