"""
Automated Test Suite: Course Prerequisite Gating and Assessment Eligibility.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from learning_system.models import (
    User, UserRole, AccountStatus, Learner, Course, CoursePrerequisite,
    Skill, Assessment, AssessmentQuestion, QuestionType, CourseEnrollment,
    EnrollmentStatus, Attempt
)
from learning_system.services import (
    AuthService, PrerequisiteService, AssessmentService, MasteryService
)


class PrerequisiteGatingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Admin & Instructor
        self.admin = User.objects.create_superuser('admin_p', 'ad@test.com', 'Pass123!', role=UserRole.PLATFORM_ADMIN, status=AccountStatus.ACTIVE)
        self.instructor = User.objects.create_user('inst_p', 'inst@test.com', 'Pass123!', role=UserRole.INSTRUCTOR, status=AccountStatus.ACTIVE)

        # Learner
        self.learner = AuthService.register_learner('student_prereq', 'student@test.com', 'Pass123!')
        self.learner.user.refresh_from_db()

        # Skills
        self.skill_py = Skill.objects.create(skill_id='SKL-PY01', name='Python Syntax', code='SKL-PY01', category='Programming')

        # Courses
        self.course_fund = Course.objects.create(
            course_id='CRS-P01',
            title='Python Fundamentals',
            code='PY101',
            description='Basics',
            is_advanced=False
        )

        self.course_adv = Course.objects.create(
            course_id='CRS-P02',
            title='Advanced Python',
            code='PY201',
            description='Advanced OOP',
            is_advanced=True
        )

        # Content Items for courses
        from learning_system.models import ContentItem, ContentSkill
        self.content_fund = ContentItem.objects.create(
            content_id='CNT-P01',
            course=self.course_fund,
            title='Python Fundamentals Module 1',
            order=1
        )
        ContentSkill.objects.create(content_item=self.content_fund, skill=self.skill_py)

        self.content_adv = ContentItem.objects.create(
            content_id='CNT-P02',
            course=self.course_adv,
            title='Advanced Python Module 1',
            order=1
        )
        ContentSkill.objects.create(content_item=self.content_adv, skill=self.skill_py)

        # Assessment
        self.gating_asm = Assessment.objects.create(
            assessment_id='ASM-GATE01',
            course=self.course_fund,
            skill=self.skill_py,
            title='Python Prerequisite Gate Exam',
            passing_percentage=70.0,
            is_prerequisite_gate=True
        )

        # Questions
        AssessmentQuestion.objects.create(
            assessment=self.gating_asm,
            question_text='What is Python?',
            question_type=QuestionType.MULTIPLE_CHOICE,
            options_json=[{'key': 'A', 'text': 'Interpreted Language'}, {'key': 'B', 'text': 'Hardware Device'}],
            correct_answer='A',
            points=1.0,
            order=1
        )

        # Rule: PY201 requires PY101 completed and Gating Assessment passed >= 70%
        CoursePrerequisite.objects.create(
            course=self.course_adv,
            prerequisite_course=self.course_fund,
            required_min_mastery=70.0,
            required_assessment=self.gating_asm,
            min_score=70.0
        )

    def test_fundamental_course_enrollment_allowed(self):
        """
        Learner can freely enroll in fundamental courses.
        """
        self.client.force_authenticate(user=self.learner.user)
        res = self.client.post(f'/api/courses/{self.course_fund.course_id}/enroll')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(CourseEnrollment.objects.filter(learner=self.learner, course=self.course_fund).exists())

    def test_advanced_course_enrollment_rejected_if_prerequisites_unmet(self):
        """
        Enrolling in an advanced course without satisfying prerequisites must be rejected with 403.
        """
        self.client.force_authenticate(user=self.learner.user)
        res = self.client.post(f'/api/courses/{self.course_adv.course_id}/enroll')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(CourseEnrollment.objects.filter(learner=self.learner, course=self.course_adv).exists())

    def test_unlocks_advanced_course_after_prerequisites_and_assessment_passed(self):
        """
        Once the learner completes the fundamental course and passes the prerequisite assessment,
        the advanced course becomes unlocked.
        """
        self.client.force_authenticate(user=self.learner.user)

        # Complete fundamental course
        enrollment = CourseEnrollment.objects.create(
            learner=self.learner,
            course=self.course_fund,
            status=EnrollmentStatus.COMPLETED,
            progress_percentage=100.0
        )

        # Set required skill mastery on prerequisite skill
        from learning_system.models import SkillMastery
        SkillMastery.objects.create(
            learner=self.learner,
            skill=self.skill_py,
            mastery_percentage=85.0,
            mastery_level='MASTERED',
            attempt_count=2
        )

        # Start and pass the gating assessment
        start_res = self.client.post(f'/api/assessments/{self.gating_asm.assessment_id}/start')
        self.assertEqual(start_res.status_code, status.HTTP_200_OK)
        attempt_id = start_res.data['attempt_id']
        q_id = start_res.data['questions'][0]['id']

        # Submit correct answer 'A'
        submit_res = self.client.post(f'/api/assessments/{self.gating_asm.assessment_id}/submit', {
            'attempt_id': attempt_id,
            'responses': [{'question_id': q_id, 'selected_option': 'A'}]
        }, format='json')
        self.assertEqual(submit_res.status_code, status.HTTP_200_OK)
        self.assertTrue(submit_res.data['passed'])
        self.assertEqual(submit_res.data['score_percentage'], 100.0)

        # Now enroll in advanced course
        enroll_adv_res = self.client.post(f'/api/courses/{self.course_adv.course_id}/enroll')
        self.assertEqual(enroll_adv_res.status_code, status.HTTP_200_OK)
        self.assertTrue(CourseEnrollment.objects.filter(learner=self.learner, course=self.course_adv).exists())
