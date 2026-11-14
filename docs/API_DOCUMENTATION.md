# RESTful API Documentation
## Personalized Learning Recommendation System

The application exposes a fully RESTful Application Programming Interface (API) using JSON payloads and standard HTTP response status codes.

---

### Base URL: `/api/`

---

### 1. Authentication Endpoints

#### `POST /api/auth/register`
- **Permission**: Public (Unauthenticated)
- **Description**: Registers a new learner account with `status: PENDING`.
- **Request Body**:
  ```json
  {
    "username": "alice_johnson",
    "email": "alice@university.edu",
    "password": "SecurePassword123!",
    "first_name": "Alice",
    "last_name": "Johnson",
    "education_level": "UNDERGRADUATE",
    "learning_goals": "Master Python and distributed architectures."
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "success": true,
    "message": "Registration submitted successfully. Your account is PENDING approval by a Platform Administrator.",
    "learner_id": "LRN-000101",
    "username": "alice_johnson",
    "status": "PENDING"
  }
  ```

#### `POST /api/auth/login`
- **Permission**: Public (Unauthenticated)
- **Description**: Authenticates user credentials with lifecycle status checks.
- **Request Body**:
  ```json
  {
    "username": "alice_johnson",
    "password": "SecurePassword123!"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "message": "Welcome back, Alice!",
    "user": {
      "id": 105,
      "username": "alice_johnson",
      "email": "alice@university.edu",
      "role": "LEARNER",
      "status": "ACTIVE",
      "learner_id": "LRN-000101"
    }
  }
  ```
- **Errors**:
  - `400 Bad Request`: If credentials are invalid, or if account status is `PENDING`, `REJECTED`, or `SUSPENDED`.

---

### 2. Platform Administrator Approval Endpoints

#### `GET /api/admin/registrations/pending`
- **Permission**: `PLATFORM_ADMIN`
- **Description**: Lists all learner registrations awaiting approval.
- **Response** (`200 OK`): Array of learner profiles with status `PENDING`.

#### `POST /api/admin/registrations/{learner_id}/approve`
- **Permission**: `PLATFORM_ADMIN`
- **Description**: Approves a pending learner and activates the account.
- **Request Body**:
  ```json
  {
    "reason": "Academic credentials and student ID verified."
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "message": "Learner LRN-000101 registration APPROVED.",
    "approval": {
      "approval_id": "APR-000095",
      "learner_id": "LRN-000101",
      "decision": "APPROVED",
      "reason": "Academic credentials and student ID verified.",
      "created_at": "2026-11-14T09:40:00Z"
    }
  }
  ```

#### `POST /api/admin/registrations/{learner_id}/reject`
- **Permission**: `PLATFORM_ADMIN`
- **Description**: Rejects a registration application.

---

### 3. Courses & Prerequisite Gating Endpoints

#### `GET /api/courses`
- **Permission**: Authenticated Active Users
- **Description**: Returns all courses with real-time prerequisite eligibility evaluated for the requesting learner.
- **Response** (`200 OK`):
  ```json
  [
    {
      "course_id": "CRS-000003",
      "title": "Python Object-Oriented Programming",
      "code": "PY201",
      "difficulty": "INTERMEDIATE",
      "is_advanced": true,
      "is_enrolled": false,
      "eligibility": {
        "course_id": "CRS-000003",
        "is_advanced": true,
        "is_eligible": false,
        "can_attempt_gating_assessment": true,
        "reasons": [
          "Must complete fundamental course 'Python Fundamentals' [PY101]."
        ],
        "prerequisites_status": [...]
      }
    }
  ]
  ```

#### `POST /api/courses/{course_id}/enroll`
- **Permission**: `LEARNER`
- **Description**: Enrolls learner into course. Backend strictly verifies prerequisite rules.
- **Response** (`200 OK`): Successfully enrolled.
- **Error** (`403 Forbidden`): Returns if prerequisites are unmet.

---

### 4. Assessments & Objective Grading Endpoints

#### `POST /api/assessments/{assessment_id}/start`
- **Permission**: `LEARNER`
- **Description**: Initiates an assessment attempt. Validates gating exam eligibility.
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "attempt_id": "ATT-LRN-000001-000004",
    "assessment_id": "ASM-000001",
    "title": "Python Fundamentals Comprehensive Assessment",
    "time_limit_minutes": 30,
    "questions": [
      {
        "id": 1,
        "order": 1,
        "question_text": "What is the primary function of key syntax?",
        "question_type": "MULTIPLE_CHOICE",
        "options": [{"key": "A", "text": "Encapsulation"}, {"key": "B", "text": "Hardware"}],
        "points": 1.0
      }
    ]
  }
  ```

#### `POST /api/assessments/{assessment_id}/submit`
- **Permission**: `LEARNER`
- **Description**: Submits answers for server-side evaluation. Never trusts client scores.
- **Request Body**:
  ```json
  {
    "attempt_id": "ATT-LRN-000001-000004",
    "responses": [
      {"question_id": 1, "selected_option": "A"}
    ]
  }
  ```
- **Response** (`200 OK`): Graded score, percentage, pass/fail status, and skill mastery impact.

---

### 5. Recommendation Endpoints

#### `POST /api/recommendations/generate`
- **Permission**: `LEARNER`
- **Description**: Deterministically recalculates personalized next learning activities.

#### `GET /api/recommendations/me`
- **Permission**: `LEARNER`
- **Description**: Retrieves current active recommendations with reason codes and explanations.
- **Response** (`200 OK`):
  ```json
  [
    {
      "recommendation_id": "REC-000012",
      "rank": 1,
      "content_id": "CNT-000004",
      "title": "Control Flow & Conditionals Masterclass",
      "format": "EXERCISE",
      "difficulty": "BEGINNER",
      "course_title": "Python Fundamentals",
      "score": 115.0,
      "reason_code": "SKILL_GAP",
      "explanation": "Knowledge gap identified: your current mastery in 'Control Flow' is 35.0% (target >= 70%). Content difficulty matches your current level."
    }
  ]
  ```

---

### 6. Validation & Analytics Endpoints

#### `GET /api/admin/data-validation`
- **Permission**: `PLATFORM_ADMIN`
- **Description**: Runs validation benchmark against PKs, FKs, skill DAG, prerequisite compliance, and the 5 ground-truth anomaly cases.
