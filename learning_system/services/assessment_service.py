"""
Assessment Processing & Attempt Management Service.
Handles attempt creation, objective server-side scoring,
validation against correct answers, and mastery updates.
"""

from typing import Dict, Any, List
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from learning_system.models import (
    Learner, Assessment, AssessmentQuestion, Attempt,
    AssessmentResponse, AssessmentResult, ContentItem, CourseEnrollment,
    EnrollmentStatus
)
from learning_system.services.mastery_service import MasteryService
from learning_system.services.audit_service import AuditService
from learning_system.services.prerequisite_service import PrerequisiteService


class AssessmentService:
    @staticmethod
    def generate_next_attempt_id(learner_id: str) -> str:
        """
        Generates sequentially ordered attempt ID: ATT-<learner-id>-000001
        """
        count = Attempt.objects.filter(learner__learner_id=learner_id).count() + 1
        while True:
            candidate_id = f"ATT-{learner_id}-{count:06d}"
            if not Attempt.objects.filter(attempt_id=candidate_id).exists():
                return candidate_id
            count += 1

    @classmethod
    @transaction.atomic
    def start_assessment_attempt(cls, learner: Learner, assessment_id: str,
                                 content_item_id: str = None) -> Attempt:
        """
        Initializes an assessment attempt.
        If the assessment is a prerequisite gate, verifies prerequisite gating eligibility.
        """
        try:
            assessment = Assessment.objects.select_related('course', 'skill').get(
                assessment_id=assessment_id
            )
        except Assessment.DoesNotExist:
            raise ValidationError(f"Assessment '{assessment_id}' does not exist.")

        # If it is a prerequisite gate for an advanced course, check if learner has satisfied prerequisites
        if assessment.is_prerequisite_gate:
            advanced_courses = assessment.required_for_course_prereqs.all()
            for prereq_rule in advanced_courses:
                eligibility = PrerequisiteService.evaluate_course_eligibility(
                    learner, prereq_rule.course
                )
                if not eligibility.get("can_attempt_gating_assessment", False):
                    raise PermissionDenied(
                        f"Cannot attempt gating assessment '{assessment.title}'. "
                        "You must first complete the fundamental courses and achieve required skill mastery."
                    )

        content_item = None
        if content_item_id:
            content_item = ContentItem.objects.filter(content_id=content_item_id).first()

        attempt_count = Attempt.objects.filter(
            learner=learner,
            assessment=assessment
        ).count() + 1

        attempt_id = cls.generate_next_attempt_id(learner.learner_id)
        now = timezone.now()

        attempt = Attempt.objects.create(
            attempt_id=attempt_id,
            learner=learner,
            assessment=assessment,
            content_item=content_item,
            attempt_number=attempt_count,
            started_at=now,
            completed_at=now,
            score=0.0,
            max_score=0.0,
            percentage=0.0,
            passed=False,
            is_valid=True
        )

        return attempt

    @classmethod
    @transaction.atomic
    def submit_assessment_attempt(cls, attempt_id: str, responses: List[Dict[str, Any]],
                                  ip_address: str = None) -> Dict[str, Any]:
        """
        Objective server-side grading.
        Never trust client scores!
        Grades answers against AssessmentQuestion records, calculates percentage,
        records responses, updates skill mastery, and updates enrollment progress.
        """
        try:
            attempt = Attempt.objects.select_related('assessment', 'learner', 'assessment__skill', 'assessment__course').get(
                attempt_id=attempt_id
            )
        except Attempt.DoesNotExist:
            raise ValidationError(f"Attempt '{attempt_id}' not found.")

        # Prevent resubmitting already finalized attempt
        if hasattr(attempt, 'result'):
            raise ValidationError(f"Attempt '{attempt_id}' has already been graded.")

        assessment = attempt.assessment
        learner = attempt.learner
        questions = list(assessment.questions.all().order_by('order'))

        if not questions:
            raise ValidationError("Assessment has no questions configured.")

        # Map responses by question id
        submitted_answers = {
            r.get('question_id'): str(r.get('selected_option', '')).strip().upper()
            for r in responses
        }

        total_points = sum(q.points for q in questions)
        earned_points = 0.0
        correct_count = 0
        detailed_responses = []

        for q in questions:
            user_choice = submitted_answers.get(q.id, "")
            is_correct = (user_choice == str(q.correct_answer).strip().upper())
            points_for_q = q.points if is_correct else 0.0

            earned_points += points_for_q
            if is_correct:
                correct_count += 1

            AssessmentResponse.objects.create(
                attempt=attempt,
                question=q,
                selected_option=user_choice,
                is_correct=is_correct,
                points_earned=points_for_q
            )

            detailed_responses.append({
                "question_id": q.id,
                "question_text": q.question_text,
                "selected_option": user_choice,
                "correct_answer": q.correct_answer,
                "is_correct": is_correct,
                "points_earned": points_for_q,
                "explanation": q.explanation
            })

        percentage = round((earned_points / total_points * 100.0) if total_points > 0 else 0.0, 2)
        passed = (percentage >= assessment.passing_percentage)

        now = timezone.now()
        attempt.score = earned_points
        attempt.max_score = total_points
        attempt.percentage = percentage
        attempt.passed = passed
        attempt.completed_at = now
        attempt.save(update_fields=['score', 'max_score', 'percentage', 'passed', 'completed_at'])

        # Compute feedback
        if passed:
            feedback = f"Congratulations! You passed with {percentage:.1f}% (required: {assessment.passing_percentage:.1f}%)."
        else:
            feedback = f"Score: {percentage:.1f}%. Passing score is {assessment.passing_percentage:.1f}%. Review the recommended modules and retake the assessment."

        # Update target skill mastery
        target_skill = assessment.skill
        updated_mastery = MasteryService.calculate_skill_mastery(
            learner=learner,
            skill=target_skill,
            trigger_attempt=attempt
        )

        mastery_impact = {
            "skill_id": target_skill.skill_id,
            "skill_name": target_skill.name,
            "new_mastery_percentage": updated_mastery.mastery_percentage,
            "new_mastery_level": updated_mastery.mastery_level,
            "total_attempts": updated_mastery.attempt_count
        }

        # Create AssessmentResult record
        result = AssessmentResult.objects.create(
            attempt=attempt,
            total_questions=len(questions),
            correct_answers=correct_count,
            score_percentage=percentage,
            passed=passed,
            feedback=feedback,
            computed_mastery_impact=mastery_impact,
            created_at=now
        )

        # Update Learner activity count
        learner.total_completed_activities += 1
        learner.save(update_fields=['total_completed_activities', 'updated_at'])

        # Check and update Course Enrollment progress
        enrollment = CourseEnrollment.objects.filter(
            learner=learner,
            course=assessment.course
        ).first()

        if enrollment:
            # Calculate overall course progress: fraction of course assessments passed
            course_assessments = assessment.course.assessments.all()
            total_assessments = course_assessments.count()
            if total_assessments > 0:
                passed_assessments = Attempt.objects.filter(
                    learner=learner,
                    assessment__course=assessment.course,
                    passed=True,
                    is_valid=True
                ).values('assessment').distinct().count()

                progress_pct = round((passed_assessments / total_assessments) * 100.0, 1)
                enrollment.progress_percentage = min(progress_pct, 100.0)
                if enrollment.progress_percentage >= 100.0:
                    enrollment.status = EnrollmentStatus.COMPLETED
                    if not enrollment.completed_at:
                        enrollment.completed_at = now
                else:
                    enrollment.status = EnrollmentStatus.IN_PROGRESS
                enrollment.save()

        AuditService.log_event(
            action="ASSESSMENT_SUBMITTED",
            entity_type="Assessment",
            entity_id=assessment.assessment_id,
            actor=learner.user,
            details={
                "attempt_id": attempt.attempt_id,
                "score_percentage": percentage,
                "passed": passed,
                "skill_updated": target_skill.code,
                "mastery_percentage": updated_mastery.mastery_percentage
            },
            ip_address=ip_address
        )

        return {
            "attempt_id": attempt.attempt_id,
            "assessment_id": assessment.assessment_id,
            "title": assessment.title,
            "score": earned_points,
            "max_score": total_points,
            "score_percentage": percentage,
            "passing_percentage": assessment.passing_percentage,
            "passed": passed,
            "feedback": feedback,
            "mastery_impact": mastery_impact,
            "responses": detailed_responses
        }
