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

## 🏗️ Technology Stack

- **Presentation Layer (Tier 1)**: HTML5, CSS3 Custom Properties Design System, Vanilla ES6+ JavaScript, Responsive Grid/Flexbox layouts.
- **Application Layer (Tier 2)**: Python 3.14, Django 6.0, Django REST Framework 3.17, Django Service Layer.
- **Data Layer (Tier 3)**: MySQL Server 8.0 with Django ORM and immutable zero-padded IDs (`LRN-000001`, `CRS-000001`, `SKL-000001`, `CNT-000001`, `ATT-<learner_id>-000001`, `PATH-2026-000001`, `REC-000001`).
- **Data Processing**: Pandas 2.3, NumPy 2.3.
- **Testing**: Django Native Test Runner & DRF API Client.

---

## 🚀 Quick Start Guide

### 1. Environment Setup

Clone or navigate to the project directory:

```bash
cd C:\Users\Shanthipriya\.gemini\antigravity\scratch\personalized_learning_system
```

Copy the environment template:

```bash
cp .env.example .env
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the MySQL database and configure `.env` with your MySQL credentials. The defaults are `DB_NAME=personalized_learning_db`, `DB_USER=root`, `DB_HOST=127.0.0.1`, and `DB_PORT=3306`.

```sql
CREATE DATABASE personalized_learning_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Set `DB_ENGINE=mysql` in `.env` and set `DB_PASSWORD` to your MySQL password before starting Django.

### 2. Database Migrations

Apply database schema migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Generate Synthetic Data (Starter Mode)

Populate the database with 100 learners, 30 skills, 50 content items, 1,002 attempts, and the 5 labeled anomalies:

```bash
python manage.py generate_synthetic_data --mode STARTER --seed 20261022
```

### 4. Run Automated Data Validation Benchmarks

Execute the evaluation benchmark suite:

```bash
python manage.py validate_and_evaluate
```

### 5. Run the Automated Test Suite

```bash
python manage.py test tests
```

### 6. Start the Development Server

```bash
python manage.py runserver 8000
```

Open your browser at: **`http://127.0.0.1:8000/`**

---

## 👥 Demo Accounts (Password: `Admin12345!`)

| Role | Username | Password | Purpose & Access |
| :--- | :--- | :--- | :--- |
| **Learner** | `learner_000001` | `Admin12345!` | Personalized recommendations, mastery meters, quiz runner, learning path, catalog. |
| **Instructor** | `prof_smith` | `Admin12345!` | Course creation, skill DAG mapping, content uploader, at-risk learner monitor. |
| **Academic Admin** | `academic_admin` | `Admin12345!` | Enrollment analytics, completion rates, curriculum skill gap analysis. |
| **Support Staff** | `support_rep` | `Admin12345!` | Helpdesk queue, ticket investigation, resolution updates. |
| **Platform Admin** | `platform_admin` | `Admin12345!` | Synthetic data generator, validation benchmark, anomaly monitoring. |

*Note: The login page includes 1-click demo credential fill buttons for instant testing of all 5 roles!*

---

## 📚 Complete Technical Documentation

Full architectural and implementation documentation is available in the [`docs/`](docs/) directory:

1. [**System Architecture**](docs/SYSTEM_ARCHITECTURE.md) - Three-tier architecture, sequence flows, and Mermaid diagrams.
2. [**Database Schema**](docs/DATABASE_SCHEMA.md) - ERD, table definitions, foreign keys, and indexes.
3. [**Data Dictionary**](docs/DATA_DICTIONARY.md) - Comprehensive field-by-field entity specifications.
4. [**API Documentation**](docs/API_DOCUMENTATION.md) - Complete REST endpoint schemas and payload examples.
5. [**Recommendation Logic**](docs/RECOMMENDATION_LOGIC.md) - Mathematical formulation, ranking criteria, and reason codes.
6. [**Data Generation**](docs/DATA_GENERATION.md) - Parameterized generator specifications (seed `20261022`) and anomaly injection.
7. [**Validation Report**](docs/VALIDATION_REPORT.md) - Real-time metrics scorecard (PK uniqueness, FK integrity, Precision@3, Recall@3).
8. [**Testing Guide**](docs/TESTING.md) - Test suite execution instructions and test case coverage.
9. [**Source Manifest**](docs/SOURCE_MANIFEST.md) - Detailed directory map and source file manifest.
