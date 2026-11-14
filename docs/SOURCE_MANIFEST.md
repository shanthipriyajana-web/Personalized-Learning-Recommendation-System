# Source Manifest & Project Layout
## Personalized Learning Recommendation System

### 1. File Structure Overview

```
personalized_learning_system/
├── manage.py                                 # Django CLI entrypoint
├── requirements.txt                          # Project Python dependencies
├── .env.example                              # Environment configuration template
├── .env                                      # Active environment configuration
├── .gitignore                                # Git ignore specification
├── config/
│   ├── __init__.py
│   ├── settings.py                           # App settings, DB config, REST framework, thresholds
│   ├── urls.py                               # Top-level URL routing
│   ├── asgi.py
│   └── wsgi.py
├── learning_system/                          # Core modular application
│   ├── __init__.py
│   ├── apps.py                               # App configuration
│   ├── models.py                             # All 25 database models (RBAC, Courses, Skills, Recs)
│   ├── views.py                              # Presentation layer template views
│   ├── services/                             # Business Logic Service Layer
│   │   ├── __init__.py
│   │   ├── audit_service.py                  # Audit logging service
│   │   ├── auth_service.py                   # Registration & authentication service
│   │   ├── prerequisite_service.py           # Course prerequisite & assessment gating
│   │   ├── mastery_service.py                # Deterministic skill mastery calculations
│   │   ├── assessment_service.py             # Objective server-side assessment scoring
│   │   ├── recommendation_service.py         # Rule-based explainable recommendation engine
│   │   ├── learning_path_service.py          # Acyclic learning path generator
│   │   ├── data_generator_service.py         # Synthetic data generator (seed 20261022)
│   │   └── validation_service.py             # Benchmark evaluation & integrity validation
│   ├── api/                                  # Application REST API Layer
│   │   ├── __init__.py
│   │   ├── exceptions.py                     # Centralized exception handler
│   │   ├── permissions.py                    # Five-Role RBAC permissions
│   │   ├── serializers.py                    # DRF Serializers for all entities
│   │   ├── views.py                          # RESTful API view handlers
│   │   └── urls.py                           # API routing
│   └── management/commands/                  # Management CLI Commands
│       ├── __init__.py
│       ├── generate_synthetic_data.py        # Dataset generator command
│       └── validate_and_evaluate.py          # Validation benchmark command
├── templates/                                # HTML5 Presentation Tier
│   ├── base.html                             # Global layout, navbar, toasts
│   ├── auth/
│   │   ├── login.html                        # Sign in form
│   │   ├── register.html                     # Learner registration
│   └── dashboards/
│       ├── learner_dashboard.html            # Learner recommendations & quiz runner
│       ├── instructor_dashboard.html         # Curriculum & gating manager
│       ├── academic_dashboard.html           # Analytics & skill gap heatmaps
│       ├── support_dashboard.html            # Helpdesk queue & triaging
│       └── platform_admin_dashboard.html     # Data generator & validation benchmarks
├── static/
│   ├── css/
│   │   └── style.css                         # Modern responsive design system
│   └── js/
│       ├── api.js                            # Core fetch client & CSRF handler
│       ├── learner.js                        # Learner dashboard interactivity
│       ├── instructor.js                     # Instructor workflows
│       ├── academic.js                       # Academic analytics charts
│       ├── support.js                        # Support tickets management
│       └── admin.js                          # Benchmarks UI
├── data/
│   ├── ground_truth.json                     # Isolated ground-truth anomaly records
│   └── ground_truth.csv                      # CSV format of ground-truth anomalies
├── tests/
│   ├── __init__.py
│   ├── test_auth_rbac.py                     # Auth & RBAC test suite
│   ├── test_prerequisites.py                 # Prerequisite & gating test suite
│   ├── test_recommendations.py               # Recommendation & mastery test suite
│   └── test_validation.py                    # Validation benchmark test suite
└── docs/
    ├── README.md                             # Setup & operational manual
    ├── SYSTEM_ARCHITECTURE.md                # Three-tier architecture & Mermaid diagrams
    ├── DATABASE_SCHEMA.md                    # Database ERD & table specifications
    ├── DATA_DICTIONARY.md                    # Attribute dictionary & types
    ├── API_DOCUMENTATION.md                  # REST endpoint definitions & schemas
    ├── RECOMMENDATION_LOGIC.md               # Deterministic recommendation formulation
    ├── DATA_GENERATION.md                    # Parameterized generator specifications
    ├── VALIDATION_REPORT.md                  # Benchmark metrics & results
    ├── TESTING.md                            # Testing guide & coverage
    └── SOURCE_MANIFEST.md                    # This manifest
```
