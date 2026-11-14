# Synthetic Data Generation & Anomaly Injections
## Personalized Learning Recommendation System

### 1. Overview & Seed Specifications

The platform provides a parameterized Python data generator engineered for high-throughput batch operations and reproducibility:

- **Fixed Seed**: `20261022`
- **Reproducibility Guarantee**: Given the fixed seed, repeated executions generate identical distributions, skills, learner IDs, and question attempt sequences.
- **Modes**:
  1. **Starter Dataset**:
     - 100 Learners
     - 30 Skills
     - 50 Content Items
     - 1,002 Attempts
     - Execution Time: $\approx 5$ seconds
  2. **Full Dataset**:
     - 10,000 Learners
     - 500 Skills
     - 2,000 Content Items
     - 500,000 Attempts
     - Implemented via chunked `bulk_create` operations (batch size 1,000)

---

### 2. Generation Command

Run from the project root:

```bash
# Starter Mode (Default)
python manage.py generate_synthetic_data --mode STARTER --seed 20261022

# Full Mode
python manage.py generate_synthetic_data --mode FULL --seed 20261022
```

---

### 3. Topological Generation Pipeline

1. **System Roles**: Standard test accounts for `platform_admin`, `academic_admin`, `prof_smith` (Instructor), and `support_rep`.
2. **Skills**: Modular skill taxonomy across 6 core computer science areas.
3. **Skill Prerequisites**: Valid Directed Acyclic Graph (DAG) using lower-index dependency binding ($j < i$).
4. **Courses & Prerequisite Rules**: Fundamental courses (`PY101`, `DB101`) and Advanced gated courses (`PY102`, `PY201`, `PY301`, `WEB201`).
5. **Content Items**: Multi-format learning resources (`VIDEO`, `ARTICLE`, `EXERCISE`, `QUIZ`).
6. **Content-Skill Mappings**: Weighted association between content items and skills ($0.1 - 1.0$).
7. **Learners & Approvals**: 90% Active/Approved, 5% Pending, 3% Rejected, 2% Suspended.
8. **Attempts & Results**: Beta distribution scores centered at $72\%$ with realistic pass/fail variance.
9. **Mastery Calculations**: Computed without temporal leakage.
10. **Recommendations**: Top-5 ranked activities with reason codes.
11. **Learning Paths**: Sequential milestone trajectories.
12. **Anomaly Injections**: 5 benchmark exception scenarios.

---

### 4. Required Injected Anomaly Scenarios

The 5 required anomaly scenarios are injected with isolated ground-truth labels and exported to `data/ground_truth.json` and `data/ground_truth.csv`:

| Issue ID | Anomaly Scenario | Related Entity | Expected System Behavior |
| :--- | :--- | :--- | :--- |
| `ANOM-0001` | **Prerequisite Violation** | `REC-ANOM-0001` | Locked advanced course must NOT be recommended when prerequisites are missing. |
| `ANOM-0002` | **Invalid Timestamp Order** | `ATT-ANOM-0002` | Validation fails because `completed_at` is earlier than `started_at`. |
| `ANOM-0003` | **Nonexistent Skill Mapping** | `CNT-999999` | Validation catches content item referencing nonexistent skill ID. |
| `ANOM-0004` | **Future Attempt Leakage** | `ATT-ANOM-0004` | Historical mastery calculation rejects attempts with timestamp $> \text{cutoff}$. |
| `ANOM-0005` | **Learning Path Loop** | `PATH-ANOM-0005` | Cyclic loop repeating module without advancement is flagged. |
