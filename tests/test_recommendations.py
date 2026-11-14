"""
Automated Test Suite: Deterministic Recommendation Engine & Mastery Calculations.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from learning_system.models import (
    User, UserRole, AccountStatus, Learner, Course, Skill,
    ContentItem, ContentSkill, DifficultyLevel, RecommendationReasonCode,
    Assessment, AssessmentQuestion, QuestionType, Attempt
)
from learning_system.services import (
    AuthService, RecommendationService, MasteryService
)


class RecommendationAndMasteryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser('admin_rec', 'ar@test.com', 'Pass123!', role=UserRole.PLATFORM_ADMIN, status=AccountStatus.ACTIVE)

        self.learner = AuthService.register_learner('student_rec', 'rec@test.com', 'Pass123!')

        self.skill = Skill.objects.create(
            skill_id='SKL-REC01',
            name='Algorithms & Complexity',
            code='SKL-ALGO',
            category='Algorithms'
        )

        self.course = Course.objects.create(
            course_id='CRS-REC01',
            title='Intro to Algorithms',
            code='ALGO101',
            description='Algorithms',
            is_advanced=False
        )

        self.content = ContentItem.objects.create(
            content_id='CNT-REC01',
            course=self.course,
            title='Big-O Notation Deep Dive',
            difficulty=DifficultyLevel.BEGINNER,
            estimated_minutes=20,
            order=1
        )
        ContentSkill.objects.create(content_item=self.content, skill=self.skill, relevance_weight=1.0)

    def test_cold_start_recommendation_reason(self):
        """
        New learner with 0 attempts receives COLD_START or SKILL_GAP recommendation.
        """
        recs = RecommendationService.generate_recommendations(self.learner)
        self.assertTrue(len(recs) > 0)
        top_rec = recs[0]
        self.assertIn(top_rec['reason_code'], [RecommendationReasonCode.COLD_START, RecommendationReasonCode.SKILL_GAP])
        self.assertTrue(len(top_rec['explanation']) > 10)

    def test_mastery_deterministic_reproducibility(self):
        """
        Verifies that mastery calculation is purely deterministic and reproducible.
        """
        # Create an assessment and 2 attempts
        asm = Assessment.objects.create(
            assessment_id='ASM-REC01',
            course=self.course,
            skill=self.skill,
            title='Algorithms Quiz 1',
            passing_percentage=70.0
        )

        Attempt.objects.create(
            attempt_id=f"ATT-{self.learner.learner_id}-000001",
            learner=self.learner,
            assessment=asm,
            attempt_number=1,
            score=8.0,
            max_score=10.0,
            percentage=80.0,
            passed=True,
            is_valid=True
        )

        Attempt.objects.create(
            attempt_id=f"ATT-{self.learner.learner_id}-000002",
            learner=self.learner,
            assessment=asm,
            attempt_number=2,
            score=6.0,
            max_score=10.0,
            percentage=60.0,
            passed=False,
            is_valid=True
        )

        mastery_obj = MasteryService.calculate_skill_mastery(self.learner, self.skill)
        expected_percentage = round((80.0 + 60.0) / 2, 2)  # 70.0%
        self.assertEqual(mastery_obj.mastery_percentage, expected_percentage)
        self.assertEqual(mastery_obj.mastery_level, 'PROFICIENT')
