# Personalized Learning Recommendation System
### Enterprise Three-Tier Educational Architecture

A complete, production-grade Personalized Learning Recommendation System built with **Python 3.14**, **Django 6.0**, **Django REST Framework**, and a modern responsive **HTML5/CSS3/JavaScript** presentation layer.

The platform provides intelligent, explainable recommendations based on learner history, skill mastery levels, course prerequisites, objective assessment results, content difficulty, and curriculum completion paths.

---

## 🌟 Key System Capabilities

1. **Strict Three-Tier Architecture**: Complete decoupling of Presentation, Application, and Data layers. Frontend communicates exclusively through RESTful JSON APIs.
2. **Five-Role Access Control (RBAC)**: Distinct dashboards and permissions for **Learner**, **Instructor**, **Academic Administrator**, **Support Staff**, and **Platform Administrator**.
3. **Open Registration**: Public registrations are `ACTIVE` immediately. No administrator approval step; accounts can be `SUSPENDED` if needed.
4. **Backend Course Prerequisite & Assessment Gating**: Advanced courses (e.g. `PY201`, `PY301`) remain locked until prerequisite fundamental courses are completed and prerequisite assessments are passed with $\ge 70\%$ score.
5. **Deterministic, Explainable Recommendation Engine**: Generates ranked next learning activities with explicit reason codes (`SKILL_GAP`, `PREREQUISITES_MET`, `COLD_START`, `ASSESSMENT_FAILED`, `DIFFICULTY_MATCH`, etc.) and pedagogical justifications.
6. **Reproducible Skill Mastery Engine**: Computes mastery dynamically from valid attempts without future leakage, tracking history in `SkillMasteryHistory`.
7. **Synthetic Data Generator (Seed `20261022`)**: Generates Starter (100 learners, 1k attempts) and Full (10k learners, 500k attempts) datasets using bulk database operations.
8. **Isolated Ground-Truth Anomalies**: Injects 5 benchmark exception scenarios into `data/ground_truth.json` for data quality and compliance evaluation.
9. **Automated Validation & Evaluation Suite**: Measures PK uniqueness, FK referential integrity, prerequisite compliance rate, recommendation coverage, Precision@3, Recall@3, and mastery reproducibility.

---

## 🚀 Quick Start Guide

### 1. Environment Setup

```bash
cd C:\Users\Shanthipriya\.gemini\antigravity\scratch\personalized_learning_system
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py generate_synthetic_data --mode STARTER --seed 20261022
python manage.py validate_and_evaluate
python manage.py test tests
python manage.py runserver 8000
```

Open your browser at: **`http://127.0.0.1:8000/`**
