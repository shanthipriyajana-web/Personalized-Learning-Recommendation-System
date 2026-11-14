# Automated Testing & Verification Guide
## Personalized Learning Recommendation System

### 1. Test Suite Architecture

The system features an automated test suite verifying business rules, security boundaries, role permissions, deterministic scoring, and validation benchmarks:

| Test Module | Coverage Scope | Verified Business Rules |
| :--- | :--- | :--- |
| `tests/test_auth_rbac.py` | Authentication & RBAC | Mandatory `PENDING` status on registration, Platform Admin approval requirement, rejection handling, role isolation. |
| `tests/test_prerequisites.py` | Prerequisite Gating | Fundamental enrollment open, advanced course access blocked (`403`), prerequisite course completion verification, gating assessment passing ($\ge 70\%$). |
| `tests/test_recommendations.py` | Recommendation Engine | Cold start reasoning, deterministic score calculation, mastery calculation reproducibility without future leakage. |
| `tests/test_validation.py` | Validation & Benchmarks | Skill DAG cycle detection, PK uniqueness, FK referential integrity, and anomaly detection rate ($100\%$). |

---

### 2. Executing the Test Suite

Run the tests using Django's test runner:

```bash
# Run all tests
python manage.py test tests

# Run specific test suite with high verbosity
python manage.py test tests.test_auth_rbac -v 2
python manage.py test tests.test_prerequisites -v 2
```

---

### 3. Sample Test Output

```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
...........
----------------------------------------------------------------------
Ran 11 tests in 11.381s

OK
Destroying test database for alias 'default'...
```
