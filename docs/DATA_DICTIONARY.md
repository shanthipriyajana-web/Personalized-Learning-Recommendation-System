# Data Dictionary
## Personalized Learning Recommendation System

This document provides a comprehensive reference of all attributes, data types, constraints, and business domain definitions for the system entities.

---

### 1. User (`learning_system_user`)

| Field Name | Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | BIGINT | No | AUTO | Surrogate primary key. |
| `username` | VARCHAR(150) | No | None | Unique login handle. |
| `email` | VARCHAR(254) | No | None | Contact email address. |
| `password` | VARCHAR(128) | No | None | PBKDF2/SHA256 hashed password. |
| `role` | VARCHAR(20) | No | `'LEARNER'` | RBAC Role (`LEARNER`, `INSTRUCTOR`, `ACADEMIC_ADMIN`, `SUPPORT_STAFF`, `PLATFORM_ADMIN`). |
| `status` | VARCHAR(20) | No | `'PENDING'` | Lifecycle Status (`PENDING`, `ACTIVE`, `REJECTED`, `SUSPENDED`). |
| `phone_number` | VARCHAR(20) | Yes | NULL | Contact phone number. |
| `created_at` | DATETIME(6) | No | `timezone.now` | User registration timestamp. |
| `updated_at` | DATETIME(6) | No | `auto_now` | Timestamp of last user modification. |

---

### 2. Learner (`learning_system_learner`)

| Field Name | Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `learner_id` | VARCHAR(20) | No | None | Formatted business primary key (`LRN-000001`). |
| `user_id` | BIGINT | No | None | One-to-one foreign key referencing `User.id`. |
| `current_education_level` | VARCHAR(50) | No | `'UNDERGRADUATE'` | Academic standing (`HIGH_SCHOOL`, `UNDERGRADUATE`, `GRADUATE`, `PROFESSIONAL`). |
| `learning_goals` | LONGTEXT | No | `''` | Student self-reported learning objectives. |
| `total_completed_activities` | INT UNSIGNED | No | `0` | Running tally of completed modules and quizzes. |
| `created_at` | DATETIME(6) | No | `timezone.now` | Profile creation timestamp. |

---

### 3. Course (`learning_system_course`)

| Field Name | Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `course_id` | VARCHAR(20) | No | None | Formatted business primary key (`CRS-000001`). |
| `title` | VARCHAR(200) | No | None | Course catalog title. |
| `code` | VARCHAR(50) | No | None | Unique course code (e.g. `PY101`, `PY201`). |
| `description` | LONGTEXT | No | None | Detailed course syllabus overview. |
| `difficulty` | VARCHAR(15) | No | `'BEGINNER'` | Target level (`BEGINNER`, `INTERMEDIATE`, `ADVANCED`). |
| `is_advanced` | BOOLEAN | No | `False` | When True, course requires prerequisite gating compliance. |
| `created_by_id` | BIGINT | Yes | NULL | Instructor who authored the course. |
| `is_active` | BOOLEAN | No | `True` | Active status in curriculum catalog. |

---

### 4. CoursePrerequisite (`learning_system_courseprerequisite`)

| Field Name | Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | BIGINT | No | AUTO | Surrogate primary key. |
| `course_id` | VARCHAR(20) | No | None | Target advanced course requiring prerequisite. |
| `prerequisite_course_id` | VARCHAR(20) | No | None | Mandatory prerequisite course. |
| `required_min_mastery` | DOUBLE | No | `70.0` | Minimum skill mastery percentage required. |
| `required_assessment_id` | VARCHAR(20) | Yes | NULL | Mandatory gating assessment required for enrollment. |
| `min_score` | DOUBLE | No | `70.0` | Minimum passing score on prerequisite assessment. |

---

### 5. Skill (`learning_system_skill`)

| Field Name | Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `skill_id` | VARCHAR(20) | No | None | Formatted business primary key (`SKL-000001`). |
| `name` | VARCHAR(150) | No | None | Unique descriptive skill title. |
| `code` | VARCHAR(50) | No | None | Unique identifier code (e.g. `SKL-PY01`). |
| `category` | VARCHAR(100) | No | None | Academic category (e.g. `Algorithms`, `Databases`). |
| `description` | LONGTEXT | No | `''` | Granular pedagogical scope. |

---

### 6. Attempt (`learning_system_attempt`)

| Field Name | Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `attempt_id` | VARCHAR(50) | No | None | Formatted attempt ID (`ATT-<learner_id>-000001`). |
| `learner_id` | VARCHAR(20) | No | None | Learner submitting the assessment. |
| `assessment_id` | VARCHAR(20) | No | None | Assessment being attempted. |
| `content_item_id` | VARCHAR(20) | Yes | NULL | Content item linked to this quiz. |
| `attempt_number` | INT UNSIGNED | No | `1` | Sequential attempt counter for this assessment. |
| `score` | DOUBLE | No | `0.0` | Objectively graded earned points. |
| `max_score` | DOUBLE | No | `100.0` | Maximum possible points. |
| `percentage` | DOUBLE | No | `0.0` | Normalized score percentage ($0.0 - 100.0$). |
| `passed` | BOOLEAN | No | `False` | True if percentage $\ge$ passing threshold. |
| `is_valid` | BOOLEAN | No | `True` | Validation flag (False for anomalies/cheating). |
| `started_at` | DATETIME(6) | No | `timezone.now` | Attempt start timestamp. |
| `completed_at` | DATETIME(6) | No | `timezone.now` | Attempt submission timestamp. |

---

### 7. Recommendation (`learning_system_recommendation`)

| Field Name | Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `recommendation_id` | VARCHAR(20) | No | None | Formatted business primary key (`REC-000001`). |
| `learner_id` | VARCHAR(20) | No | None | Learner targeted by recommendation. |
| `content_item_id` | VARCHAR(20) | No | None | Recommended learning activity. |
| `course_id` | VARCHAR(20) | No | None | Course container for activity. |
| `score` | DOUBLE | No | `0.0` | Composite deterministic ranking score. |
| `rank` | INT UNSIGNED | No | `1` | Rank position ($1, 2, 3 \dots$). |
| `reason_code` | VARCHAR(30) | No | None | Reason code (`SKILL_GAP`, `COLD_START`, etc.). |
| `explanation` | LONGTEXT | No | None | Explainable pedagogical justification. |
| `is_active` | BOOLEAN | No | `True` | Currently active on learner dashboard. |
| `generated_at` | DATETIME(6) | No | `timezone.now` | Generation timestamp. |
