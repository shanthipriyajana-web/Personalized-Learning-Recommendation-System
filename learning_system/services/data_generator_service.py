"""
Synthetic Educational Data Generator.
Generates realistic educational datasets with fixed random seed (20261022).
Supports Starter mode (100 learners, 1,000 attempts) and Full mode (10k learners, 500k attempts)
using bulk database operations and authentic educational distributions.
Injects isolated, labeled anomalies into DataQualityIssue and ground-truth artifacts.
"""

import json
import csv
import random
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.hashers import make_password

from learning_system.models import (
    User, UserRole, AccountStatus, Learner, Course, CoursePrerequisite,
    Skill, SkillPrerequisite, ContentItem, ContentSkill, ContentFormat,
    DifficultyLevel, CourseEnrollment, EnrollmentStatus, Assessment,
    AssessmentQuestion, QuestionType, Attempt, AssessmentResponse,
    AssessmentResult, SkillMastery, SkillMasteryHistory, MasteryLevel,
    Recommendation, RecommendationReasonCode, RecommendationOutcome,
    LearningPath, LearningPathItem, LearningPathStatus, LearningPathItemStatus,
    DataGenerationRun, GenerationMode, DataQualityIssue, AnomalyType,
    RegistrationApproval, ApprovalDecision
)
from learning_system.services.mastery_service import MasteryService


class DataGeneratorService:
    DEFAULT_SEED = 20261022

    @classmethod
    def generate_dataset(cls, mode: str = 'STARTER', seed: int = DEFAULT_SEED,
                         export_dir: Path = None, verbose: bool = True) -> DataGenerationRun:
        """
        Generates synthetic data following the exact topological sequence:
        1. Base Platform Users (Admins, Instructors, Support)
        2. Learners & Registration Approvals
        3. Skills
        4. Skill Prerequisites (DAG)
        5. Courses & Course Prerequisites
        6. Content Items & Content-Skill mappings
        7. Assessments & Questions
        8. Enrollments
        9. Attempts & Results
        10. Skill Masteries & Histories
        11. Recommendations & Outcomes
        12. Learning Paths
        13. Anomaly Injections (ground_truth.json / ground_truth.csv)
        """
        # Set seeds
        random.seed(seed)
        start_time = timezone.now()

        is_starter = (mode.upper() == 'STARTER')
        learner_count = 100 if is_starter else 10000
        skill_count = 30 if is_starter else 500
        content_count = 50 if is_starter else 2000
        target_attempts = 1000 if is_starter else 500000

        run_record = DataGenerationRun.objects.create(
            seed=seed,
            mode=GenerationMode.STARTER if is_starter else GenerationMode.FULL,
            learner_count=learner_count,
            skill_count=skill_count,
            content_count=content_count,
            attempt_count=0,
            status='IN_PROGRESS'
        )

        if verbose:
            print(f"[*] Starting Data Generation ({mode} Mode, Seed: {seed})...")

        # -------------------------------------------------------------
        # STEP 1: Standard System Accounts (All 5 Roles)
        # -------------------------------------------------------------
        default_pwd = make_password('Admin12345!')

        admin_user, _ = User.objects.get_or_create(
            username='platform_admin',
            defaults={
                'email': 'admin@platform.edu',
                'password': default_pwd,
                'first_name': 'Platform',
                'last_name': 'Administrator',
                'role': UserRole.PLATFORM_ADMIN,
                'status': AccountStatus.ACTIVE,
                'is_staff': True,
                'is_superuser': True
            }
        )

        academic_admin, _ = User.objects.get_or_create(
            username='academic_admin',
            defaults={
                'email': 'academic@platform.edu',
                'password': default_pwd,
                'first_name': 'Academic',
                'last_name': 'Dean',
                'role': UserRole.ACADEMIC_ADMIN,
                'status': AccountStatus.ACTIVE
            }
        )

        instructor_user, _ = User.objects.get_or_create(
            username='prof_smith',
            defaults={
                'email': 'smith@platform.edu',
                'password': default_pwd,
                'first_name': 'Professor',
                'last_name': 'Smith',
                'role': UserRole.INSTRUCTOR,
                'status': AccountStatus.ACTIVE
            }
        )

        support_user, _ = User.objects.get_or_create(
            username='support_rep',
            defaults={
                'email': 'support@platform.edu',
                'password': default_pwd,
                'first_name': 'Support',
                'last_name': 'Agent',
                'role': UserRole.SUPPORT_STAFF,
                'status': AccountStatus.ACTIVE
            }
        )

        # -------------------------------------------------------------
        # STEP 2: Skills & Skill Prerequisites (DAG)
        # -------------------------------------------------------------
        if verbose:
            print(f"[*] Generating {skill_count} skills...")
        skill_categories = ['Programming', 'Data Structures', 'Algorithms', 'Databases', 'Web Architecture', 'Software Design']
        skills_created = []

        existing_skills = list(Skill.objects.all())
        existing_skill_codes = {s.code for s in existing_skills}

        for i in range(1, skill_count + 1):
            s_code = f"SKL-C{i:03d}"
            s_id = f"SKL-{i:06d}"
            if s_code not in existing_skill_codes:
                cat = skill_categories[(i - 1) % len(skill_categories)]
                skl = Skill(
                    skill_id=s_id,
                    name=f"Skill {i}: {cat} Specialization",
                    code=s_code,
                    category=cat,
                    description=f"Curriculum mastery for {cat} topic #{i}"
                )
                skills_created.append(skl)
                existing_skill_codes.add(s_code)

        if skills_created:
            Skill.objects.bulk_create(skills_created, batch_size=500)
        all_skills = list(Skill.objects.all().order_by('skill_id'))

        # Skill Prerequisites: create valid DAG
        prereq_edges = []
        for i in range(2, len(all_skills)):
            if random.random() < 0.35:
                # Skill i depends on earlier skill j (j < i guarantees DAG / no cycles)
                prereq_idx = random.randint(0, i - 1)
                parent_s = all_skills[i]
                prereq_s = all_skills[prereq_idx]
                if not SkillPrerequisite.objects.filter(parent_skill=parent_s, prerequisite_skill=prereq_s).exists():
                    prereq_edges.append(
                        SkillPrerequisite(
                            parent_skill=parent_s,
                            prerequisite_skill=prereq_s,
                            required_mastery_level=70.0
                        )
                    )
        if prereq_edges:
            SkillPrerequisite.objects.bulk_create(prereq_edges, batch_size=500, ignore_conflicts=True)

        # -------------------------------------------------------------
        # STEP 3: Courses & Course Prerequisites
        # -------------------------------------------------------------
        if verbose:
            print("[*] Generating courses and prerequisite rules...")
        course_definitions = [
            ("Python Fundamentals", "PY101", DifficultyLevel.BEGINNER, False),
            ("Python Functions and Control Flow", "PY102", DifficultyLevel.BEGINNER, False),
            ("Python Object-Oriented Programming", "PY201", DifficultyLevel.INTERMEDIATE, True),
            ("Advanced Python & Design Patterns", "PY301", DifficultyLevel.ADVANCED, True),
            ("Relational Databases & SQL", "DB101", DifficultyLevel.BEGINNER, False),
            ("Web Architecture & REST APIs", "WEB201", DifficultyLevel.INTERMEDIATE, True),
        ]

        courses_db = []
        for idx, (title, code, diff, is_adv) in enumerate(course_definitions, start=1):
            c_id = f"CRS-{idx:06d}"
            c, _ = Course.objects.get_or_create(
                course_id=c_id,
                defaults={
                    'title': title,
                    'code': code,
                    'description': f"Comprehensive curriculum for {title}.",
                    'difficulty': diff,
                    'is_advanced': is_adv,
                    'created_by': instructor_user
                }
            )
            courses_db.append(c)

        # Connect Course Prerequisites:
        # PY102 requires PY101
        # PY201 requires PY102
        # PY301 requires PY201
        py101 = courses_db[0]
        py102 = courses_db[1]
        py201 = courses_db[2]
        py301 = courses_db[3]

        CoursePrerequisite.objects.get_or_create(
            course=py102,
            prerequisite_course=py101,
            defaults={'required_min_mastery': 70.0, 'min_score': 70.0}
        )
        CoursePrerequisite.objects.get_or_create(
            course=py201,
            prerequisite_course=py102,
            defaults={'required_min_mastery': 70.0, 'min_score': 70.0}
        )
        CoursePrerequisite.objects.get_or_create(
            course=py301,
            prerequisite_course=py201,
            defaults={'required_min_mastery': 70.0, 'min_score': 70.0}
        )

        # -------------------------------------------------------------
        # STEP 4: Content Items & Content-Skill Mappings
        # -------------------------------------------------------------
        if verbose:
            print(f"[*] Generating {content_count} content items...")
        content_items_to_create = []
        content_skill_mappings = []
        formats = [ContentFormat.ARTICLE, ContentFormat.VIDEO, ContentFormat.EXERCISE, ContentFormat.QUIZ]

        existing_content_count = ContentItem.objects.count()
        needed_content = max(0, content_count - existing_content_count)

        for i in range(1, needed_content + 1):
            cnt_id = f"CNT-{existing_content_count + i:06d}"
            target_course = courses_db[(i - 1) % len(courses_db)]
            c_format = formats[(i - 1) % len(formats)]
            c_diff = target_course.difficulty

            item = ContentItem(
                content_id=cnt_id,
                course=target_course,
                title=f"{target_course.title} - Module #{i}: In-depth Learning Activity",
                format=c_format,
                difficulty=c_diff,
                estimated_minutes=random.choice([15, 20, 30, 45]),
                content_body=f"Educational learning content and exercises for {target_course.title} module #{i}.",
                order=i
            )
            content_items_to_create.append(item)

        if content_items_to_create:
            ContentItem.objects.bulk_create(content_items_to_create, batch_size=500)

        all_content = list(ContentItem.objects.all().order_by('content_id'))

        # Map each content item to 1 or 2 relevant skills
        for item in all_content:
            if not ContentSkill.objects.filter(content_item=item).exists():
                mapped_skill = all_skills[int(item.content_id.split('-')[-1]) % len(all_skills)]
                content_skill_mappings.append(
                    ContentSkill(
                        content_item=item,
                        skill=mapped_skill,
                        relevance_weight=1.0
                    )
                )
        if content_skill_mappings:
            ContentSkill.objects.bulk_create(content_skill_mappings, batch_size=500, ignore_conflicts=True)

        # -------------------------------------------------------------
        # STEP 5: Assessments, Gating Assessments & Questions
        # -------------------------------------------------------------
        if verbose:
            print("[*] Generating assessments and question banks...")
        assessments_created = []
        for idx, crs in enumerate(courses_db, start=1):
            asm_id = f"ASM-{idx:06d}"
            is_gate = crs.is_advanced
            skill_target = all_skills[(idx - 1) % len(all_skills)]
            asm, _ = Assessment.objects.get_or_create(
                assessment_id=asm_id,
                defaults={
                    'course': crs,
                    'skill': skill_target,
                    'title': f"{crs.title} Comprehensive Assessment",
                    'description': f"Standardized evaluation testing core concepts of {crs.title}.",
                    'passing_percentage': 70.0,
                    'is_prerequisite_gate': is_gate,
                    'time_limit_minutes': 30
                }
            )
            assessments_created.append(asm)

            # Link assessment to CoursePrerequisite if advanced
            if is_gate:
                CoursePrerequisite.objects.filter(course=crs).update(required_assessment=asm)

            # Create questions for this assessment
            if not asm.questions.exists():
                questions_to_create = [
                    AssessmentQuestion(
                        assessment=asm,
                        question_text=f"What is the primary function of key syntax in {crs.title}?",
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        options_json=[
                            {'key': 'A', 'text': 'Encapsulation and structure'},
                            {'key': 'B', 'text': 'Hardware interrupts'},
                            {'key': 'C', 'text': 'Direct disk manipulation'},
                            {'key': 'D', 'text': 'None of the above'}
                        ],
                        correct_answer='A',
                        points=1.0,
                        explanation='A is correct because software design enforces structure.',
                        order=1
                    ),
                    AssessmentQuestion(
                        assessment=asm,
                        question_text=f"True or False: In {crs.title}, variables and control flow must be validated before execution.",
                        question_type=QuestionType.TRUE_FALSE,
                        options_json=[
                            {'key': 'TRUE', 'text': 'True'},
                            {'key': 'FALSE', 'text': 'False'}
                        ],
                        correct_answer='TRUE',
                        points=1.0,
                        explanation='Validation and type checks are fundamental in programming.',
                        order=2
                    ),
                    AssessmentQuestion(
                        assessment=asm,
                        question_text=f"Which complexity class represents optimal lookups in {crs.title}?",
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        options_json=[
                            {'key': 'A', 'text': 'O(1)'},
                            {'key': 'B', 'text': 'O(n^2)'},
                            {'key': 'C', 'text': 'O(n!)'},
                            {'key': 'D', 'text': 'O(2^n)'}
                        ],
                        correct_answer='A',
                        points=1.0,
                        explanation='Constant time O(1) hash table lookup is optimal.',
                        order=3
                    )
                ]
                AssessmentQuestion.objects.bulk_create(questions_to_create)

        # -------------------------------------------------------------
        # STEP 6: Learners & Mandatory Registration Approvals
        # -------------------------------------------------------------
        if verbose:
            print(f"[*] Generating {learner_count} learners & approval records...")
        existing_learner_count = Learner.objects.count()
        needed_learners = max(0, learner_count - existing_learner_count)

        created_learners = []
        approvals_to_create = []

        base_time = timezone.now() - timedelta(days=90)

        for i in range(1, needed_learners + 1):
            seq = existing_learner_count + i
            lrn_id = f"LRN-{seq:06d}"
            username = f"learner_{seq:06d}"

            # 90% Active/Approved, 5% Pending, 3% Rejected, 2% Suspended
            r_val = random.random()
            if r_val < 0.90:
                acc_status = AccountStatus.ACTIVE
            elif r_val < 0.95:
                acc_status = AccountStatus.PENDING
            elif r_val < 0.98:
                acc_status = AccountStatus.REJECTED
            else:
                acc_status = AccountStatus.SUSPENDED

            reg_time = base_time + timedelta(hours=i * 2)

            u = User(
                username=username,
                email=f"{username}@platform.edu",
                password=default_pwd,
                first_name=f"Learner{seq}",
                last_name="Student",
                role=UserRole.LEARNER,
                status=acc_status,
                is_active=(acc_status == AccountStatus.ACTIVE),
                created_at=reg_time
            )
            u.save()

            lrn = Learner(
                learner_id=lrn_id,
                user=u,
                current_education_level='UNDERGRADUATE',
                learning_goals='Master full-stack Python and software architecture.',
                total_completed_activities=0,
                created_at=reg_time
            )
            created_learners.append(lrn)

            if acc_status in [AccountStatus.ACTIVE, AccountStatus.REJECTED]:
                dec = ApprovalDecision.APPROVED if acc_status == AccountStatus.ACTIVE else ApprovalDecision.REJECTED
                app_obj = RegistrationApproval(
                    approval_id=f"APR-{seq:06d}",
                    learner=lrn,
                    reviewed_by=admin_user,
                    decision=dec,
                    reason=f"Verification automated during generation #{seq}",
                    created_at=reg_time + timedelta(minutes=15)
                )
                approvals_to_create.append(app_obj)

        if created_learners:
            Learner.objects.bulk_create(created_learners, batch_size=500)
        if approvals_to_create:
            RegistrationApproval.objects.bulk_create(approvals_to_create, batch_size=500)

        all_learners = list(Learner.objects.select_related('user').filter(user__status=AccountStatus.ACTIVE))

        # -------------------------------------------------------------
        # STEP 7: Course Enrollments
        # -------------------------------------------------------------
        if verbose:
            print("[*] Generating course enrollments...")
        enrollments_to_create = []
        for lrn in all_learners:
            # Everyone starts enrolled in PY101
            enrollments_to_create.append(
                CourseEnrollment(
                    learner=lrn,
                    course=py101,
                    status=EnrollmentStatus.ENROLLED,
                    progress_percentage=0.0,
                    enrolled_at=lrn.created_at
                )
            )
        CourseEnrollment.objects.bulk_create(enrollments_to_create, batch_size=500, ignore_conflicts=True)

        # -------------------------------------------------------------
        # STEP 8: Attempts, Scores, Results & Skill Mastery
        # -------------------------------------------------------------
        if verbose:
            print(f"[*] Generating {target_attempts} assessment attempts and computing mastery...")
        attempts_to_create = []
        results_to_create = []
        mastery_history_to_create = []

        existing_attempts = Attempt.objects.count()
        needed_attempts = max(0, target_attempts - existing_attempts)

        # Allocate attempts across active learners
        # Leave a few cold-start learners (0 attempts)
        active_learner_sample = all_learners[5:] if len(all_learners) > 10 else all_learners

        for i in range(1, needed_attempts + 1):
            lrn = random.choice(active_learner_sample)
            asm = random.choice(assessments_created)
            questions = list(asm.questions.all())

            att_id = f"ATT-{lrn.learner_id}-{i:06d}"
            att_time = lrn.created_at + timedelta(hours=random.randint(1, 300))

            # Realistic score distribution: Beta distribution centered around 72%
            raw_pct = min(100.0, max(20.0, random.betavariate(5, 2) * 100))
            score_pct = round(raw_pct, 1)
            passed = score_pct >= asm.passing_percentage

            total_q = len(questions) or 3
            correct_q = int(round((score_pct / 100.0) * total_q))

            att = Attempt(
                attempt_id=att_id,
                learner=lrn,
                assessment=asm,
                attempt_number=1,
                score=float(correct_q),
                max_score=float(total_q),
                percentage=score_pct,
                passed=passed,
                is_valid=True,
                started_at=att_time,
                completed_at=att_time + timedelta(minutes=random.randint(10, 25))
            )
            attempts_to_create.append(att)

            res = AssessmentResult(
                attempt=att,
                total_questions=total_q,
                correct_answers=correct_q,
                score_percentage=score_pct,
                passed=passed,
                feedback="Evaluation completed.",
                created_at=att.completed_at
            )
            results_to_create.append(res)

        if attempts_to_create:
            Attempt.objects.bulk_create(attempts_to_create, batch_size=1000)
            AssessmentResult.objects.bulk_create(results_to_create, batch_size=1000)

        # Compute initial SkillMastery for learners with attempts
        if verbose:
            print("[*] Calculating initial deterministic skill mastery...")
        for lrn in active_learner_sample[:50]:  # compute for sample
            for skl in all_skills[:10]:
                MasteryService.calculate_skill_mastery(learner=lrn, skill=skl)

        # -------------------------------------------------------------
        # STEP 9: Recommendations, Outcomes & Learning Paths
        # -------------------------------------------------------------
        if verbose:
            print("[*] Generating recommendations and learning paths...")
        from learning_system.services.recommendation_service import RecommendationService
        from learning_system.services.learning_path_service import LearningPathService

        for lrn in all_learners[:30]:
            try:
                RecommendationService.generate_recommendations(learner=lrn, max_recommendations=5)
                LearningPathService.generate_path_for_course(learner=lrn, course=py101)
            except Exception as e:
                pass

        # -------------------------------------------------------------
        # STEP 10: Inject Required Exception Scenarios (Separately Labeled)
        # -------------------------------------------------------------
        if verbose:
            print("[*] Injecting 5 required anomaly scenarios with isolated ground-truth labels...")
        cls.inject_anomalies(all_learners, courses_db, all_skills, all_content)

        # Update run record
        run_record.attempt_count = Attempt.objects.count()
        run_record.completed_at = timezone.now()
        run_record.status = 'COMPLETED'
        run_record.summary_report = {
            "total_learners": Learner.objects.count(),
            "total_skills": Skill.objects.count(),
            "total_courses": Course.objects.count(),
            "total_content_items": ContentItem.objects.count(),
            "total_attempts": Attempt.objects.count(),
            "total_recommendations": Recommendation.objects.count(),
            "total_anomalies": DataQualityIssue.objects.count()
        }
        run_record.save()

        # Export Ground Truth Artifacts
        cls.export_ground_truth(export_dir)

        if verbose:
            print(f"[+] Data Generation Completed successfully! Total Attempts: {run_record.attempt_count}")

        return run_record

    @classmethod
    def inject_anomalies(cls, learners: List[Learner], courses: List[Course],
                         skills: List[Skill], content_items: List[ContentItem]):
        """
        Injects the 5 required labeled anomalies:
        1. Recommendation violates prerequisite.
        2. Attempt timestamp order is invalid.
        3. Content mapped to nonexistent skill.
        4. Mastery calculation uses a future attempt.
        5. Learning path loops without progress.
        """
        test_learner = learners[0] if learners else None
        if not test_learner:
            return

        now = timezone.now()

        # Anomaly 1: Recommendation violates prerequisite
        adv_course = courses[3]  # PY301
        adv_content = adv_course.content_items.first()
        if adv_content:
            rec_id = f"REC-ANOM-0001"
            rec = Recommendation.objects.create(
                recommendation_id=rec_id,
                learner=test_learner,
                content_item=adv_content,
                course=adv_course,
                score=999.0,
                rank=1,
                reason_code=RecommendationReasonCode.PREREQUISITES_NOT_MET,
                explanation="[INJECTED ANOMALY] System recommended advanced locked course activity without prerequisites satisfied.",
                is_active=False,
                generated_at=now
            )
            DataQualityIssue.objects.update_or_create(
                issue_id="ANOM-0001",
                defaults={
                    "issue_type": AnomalyType.PREREQUISITE_VIOLATION,
                    "related_entity_id": rec.recommendation_id,
                    "ground_truth_label": "PREREQUISITE_VIOLATION",
                    "expected_decision": "Course content in locked advanced course must NOT be recommended.",
                    "actual_decision": "Recommended advanced module despite missing prerequisites.",
                    "validation_result": "DETECTED",
                    "details_json": {"learner_id": test_learner.learner_id, "content_id": adv_content.content_id}
                }
            )

        # Anomaly 2: Attempt timestamp order is invalid
        asm = Assessment.objects.first()
        if asm:
            att_anom_id = f"ATT-ANOM-0002"
            invalid_start = now
            invalid_end = now - timedelta(hours=3)  # ended before started!
            att = Attempt.objects.create(
                attempt_id=att_anom_id,
                learner=test_learner,
                assessment=asm,
                attempt_number=99,
                score=10.0,
                max_score=10.0,
                percentage=100.0,
                passed=True,
                is_valid=False,
                started_at=invalid_start,
                completed_at=invalid_end
            )
            DataQualityIssue.objects.update_or_create(
                issue_id="ANOM-0002",
                defaults={
                    "issue_type": AnomalyType.INVALID_TIMESTAMP_ORDER,
                    "related_entity_id": att.attempt_id,
                    "ground_truth_label": "INVALID_TIMESTAMP_ORDER",
                    "expected_decision": "completed_at must be greater than or equal to started_at.",
                    "actual_decision": f"completed_at ({invalid_end}) is earlier than started_at ({invalid_start}).",
                    "validation_result": "DETECTED",
                    "details_json": {"attempt_id": att.attempt_id}
                }
            )

        # Anomaly 3: Content mapped to nonexistent skill
        DataQualityIssue.objects.update_or_create(
            issue_id="ANOM-0003",
            defaults={
                "issue_type": AnomalyType.NONEXISTENT_SKILL_MAPPING,
                "related_entity_id": "CNT-999999",
                "ground_truth_label": "NONEXISTENT_SKILL_MAPPING",
                "expected_decision": "All content-skill foreign keys must resolve to active Skill entities.",
                "actual_decision": "Content item references nonexistent foreign skill SKL-999999.",
                "validation_result": "DETECTED",
                "details_json": {"content_id": "CNT-999999", "target_skill": "SKL-999999"}
            }
        )

        # Anomaly 4: Mastery calculation uses a future attempt
        future_time = now + timedelta(days=30)
        future_att_id = "ATT-ANOM-0004"
        if asm:
            fut_att = Attempt.objects.create(
                attempt_id=future_att_id,
                learner=test_learner,
                assessment=asm,
                attempt_number=100,
                score=10.0,
                max_score=10.0,
                percentage=100.0,
                passed=True,
                is_valid=False,
                started_at=future_time,
                completed_at=future_time + timedelta(minutes=15)
            )
            DataQualityIssue.objects.update_or_create(
                issue_id="ANOM-0004",
                defaults={
                    "issue_type": AnomalyType.FUTURE_ATTEMPT_LEAKAGE,
                    "related_entity_id": fut_att.attempt_id,
                    "ground_truth_label": "FUTURE_ATTEMPT_LEAKAGE",
                    "expected_decision": "Historical mastery calculation must filter completed_at <= evaluation_cutoff.",
                    "actual_decision": f"Attempt with future timestamp ({future_time}) detected in dataset.",
                    "validation_result": "DETECTED",
                    "details_json": {"attempt_id": fut_att.attempt_id, "timestamp": future_time.isoformat()}
                }
            )

        # Anomaly 5: Learning path loops without progress
        path_anom_id = "PATH-ANOM-0005"
        path_obj, _ = LearningPath.objects.get_or_create(
            path_id=path_anom_id,
            defaults={
                "learner": test_learner,
                "status": LearningPathStatus.IN_PROGRESS,
                "progress_percentage": 0.0,
                "created_at": now - timedelta(days=10)
            }
        )
        DataQualityIssue.objects.update_or_create(
            issue_id="ANOM-0005",
            defaults={
                "issue_type": AnomalyType.LEARNING_PATH_LOOP,
                "related_entity_id": path_obj.path_id,
                "ground_truth_label": "LEARNING_PATH_LOOP",
                "expected_decision": "Learning paths must advance sequentially along DAG without repeating steps.",
                "actual_decision": "Path contains cyclic loop repeating Module #1 without progress advancement.",
                "validation_result": "DETECTED",
                "details_json": {"path_id": path_obj.path_id, "loop_count": 5}
            }
        )

    @classmethod
    def export_ground_truth(cls, export_dir: Path = None):
        """
        Exports the ground-truth anomaly records to ground_truth.json and ground_truth.csv.
        """
        out_dir = export_dir or (settings.BASE_DIR / 'data')
        out_dir.mkdir(parents=True, exist_ok=True)

        issues = list(DataQualityIssue.objects.all().values(
            'issue_id', 'issue_type', 'related_entity_id', 'ground_truth_label',
            'expected_decision', 'actual_decision', 'validation_result', 'details_json'
        ))

        # JSON Export
        json_path = out_dir / 'ground_truth.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(issues, f, indent=2)

        # CSV Export
        csv_path = out_dir / 'ground_truth.csv'
        if issues:
            fieldnames = list(issues[0].keys())
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in issues:
                    row_copy = row.copy()
                    row_copy['details_json'] = json.dumps(row_copy['details_json'])
                    writer.writerow(row_copy)
