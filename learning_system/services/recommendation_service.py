"""
Deterministic Explainable Personalized Learning Recommendation Engine.
Produces rule-based, reproducible learning activity recommendations
with explicit reason codes and pedagogical explanations.
"""

from typing import List, Dict, Any, Optional
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from learning_system.models import (
    Learner, Course, Skill, ContentItem, ContentSkill, Attempt,
    SkillMastery, Recommendation, RecommendationReasonCode,
    DifficultyLevel, CourseEnrollment, EnrollmentStatus
)
from learning_system.services.prerequisite_service import PrerequisiteService
from learning_system.services.mastery_service import MasteryService
from learning_system.services.audit_service import AuditService


class RecommendationService:
    @staticmethod
    def generate_next_recommendation_id() -> str:
        """
        Generates sequentially ordered ID: REC-000001
        """
        count = Recommendation.objects.count() + 1
        while True:
            candidate_id = f"REC-{count:06d}"
            if not Recommendation.objects.filter(recommendation_id=candidate_id).exists():
                return candidate_id
            count += 1

    @classmethod
    @transaction.atomic
    def generate_recommendations(cls, learner: Learner, max_recommendations: int = 5,
                                 actor=None, ip_address: str = None) -> List[Dict[str, Any]]:
        """
        Core Recommendation Pipeline:
        1. Retrieve learner history & attempt profile.
        2. Compute skill masteries from valid past attempts.
        3. Identify low mastery skills (gaps) and recent failed attempts.
        4. Validate course prerequisites and filter/boost candidate activities.
        5. Evaluate content difficulty relative to learner skill level.
        6. Compute deterministic ranking score.
        7. Tag with explainable reason codes.
        8. Persist and return top-K recommendations.
        """
        # Deactivate old active recommendations for this learner to maintain fresh state
        Recommendation.objects.filter(learner=learner, is_active=True).update(is_active=False)

        # 1. Check for Cold Start Learner (no past attempts)
        total_attempts = Attempt.objects.filter(learner=learner, is_valid=True).count()
        is_cold_start = (total_attempts == 0)

        # 2. Get Recent Failed Assessments (for targeted revision)
        recent_failed_attempts = list(Attempt.objects.filter(
            learner=learner,
            passed=False,
            is_valid=True
        ).order_by('-completed_at')[:3])

        failed_skill_ids = set()
        for f_att in recent_failed_attempts:
            if f_att.assessment and f_att.assessment.skill:
                failed_skill_ids.add(f_att.assessment.skill.skill_id)

        # 3. Retrieve Learner's current skill masteries
        mastery_map: Dict[str, float] = {}
        for sm in SkillMastery.objects.filter(learner=learner):
            mastery_map[sm.skill.skill_id] = sm.mastery_percentage

        # 4. Identify Content Items already mastered / passed by learner
        # Passed quiz contents or attempts with >= 85%
        mastered_content_ids = set(Attempt.objects.filter(
            learner=learner,
            passed=True,
            is_valid=True,
            content_item__isnull=False
        ).values_list('content_item_id', flat=True))

        # 5. Fetch candidate content items
        # Consider all active content items across all active courses
        candidates = ContentItem.objects.filter(
            is_active=True,
            course__is_active=True
        ).select_related('course').prefetch_related('skill_mappings__skill')

        scored_candidates = []

        for item in candidates:
            # Check course eligibility via PrerequisiteService
            course_eligibility = PrerequisiteService.evaluate_course_eligibility(
                learner=learner,
                course=item.course
            )

            # Check if content was already mastered
            is_already_mastered = item.content_id in mastered_content_ids

            # Find skills mapped to this content item
            item_skills = list(item.skill_mappings.all())
            primary_skill = item_skills[0].skill if item_skills else None
            primary_relevance = item_skills[0].relevance_weight if item_skills else 1.0

            skill_id = primary_skill.skill_id if primary_skill else None
            current_mastery = mastery_map.get(skill_id, 0.0) if skill_id else 0.0

            # Difficulty evaluation
            preferred_diff = DifficultyLevel.BEGINNER
            if current_mastery < 40.0:
                preferred_diff = DifficultyLevel.BEGINNER
            elif current_mastery < 70.0:
                preferred_diff = DifficultyLevel.INTERMEDIATE
            else:
                preferred_diff = DifficultyLevel.ADVANCED

            diff_matched = (item.difficulty == preferred_diff)

            # If the course is an advanced locked course, learner CANNOT access this content yet!
            if not course_eligibility["is_eligible"]:
                # Content in locked advanced courses is not eligible for direct learning recommendation
                continue

            # If already mastered with high score, exclude from next activity recommendation
            if is_already_mastered and current_mastery >= 85.0:
                continue

            # Deterministic Ranking Formulation:
            # Score = GapScore + DifficultyScore + RelevanceScore + ContextBoost
            score = 0.0
            primary_reason = RecommendationReasonCode.SKILL_GAP
            explanation_parts = []

            # Factor A: Cold Start Case
            if is_cold_start:
                if not item.course.is_advanced and item.difficulty == DifficultyLevel.BEGINNER:
                    score += 150.0
                    primary_reason = RecommendationReasonCode.COLD_START
                    explanation_parts.append(
                        "Recommended as an essential foundational module for your initial learning trajectory."
                    )
                else:
                    score += 20.0

            # Factor B: Targeted Assessment Revision
            elif skill_id in failed_skill_ids:
                score += 120.0
                primary_reason = RecommendationReasonCode.ASSESSMENT_FAILED
                explanation_parts.append(
                    f"Targeted revision activity addressing key gaps from your recent assessment on '{primary_skill.name}'."
                )

            # Factor C: Skill Gap (Mastery < 70%)
            elif current_mastery < 70.0:
                gap = 100.0 - current_mastery
                score += (gap * 1.0)
                primary_reason = RecommendationReasonCode.SKILL_GAP
                explanation_parts.append(
                    f"Knowledge gap identified: your current mastery in '{primary_skill.name if primary_skill else 'this topic'}' is {current_mastery:.1f}% (target >= 70%)."
                )

            # Factor D: Prerequisite Met Advanced Activity
            elif course_eligibility.get("is_advanced") and course_eligibility.get("is_eligible"):
                score += 80.0
                primary_reason = RecommendationReasonCode.PREREQUISITES_MET
                explanation_parts.append(
                    f"Prerequisites satisfied! You have unlocked this advanced module in '{item.course.title}'."
                )

            # Factor E: Not Yet Completed
            elif not is_already_mastered:
                score += 50.0
                primary_reason = RecommendationReasonCode.NOT_COMPLETED
                explanation_parts.append(
                    f"Core curriculum activity in '{item.course.title}' scheduled for completion."
                )

            # Difficulty Adjustment
            if diff_matched:
                score += 25.0
                explanation_parts.append(
                    f"Content difficulty ({item.difficulty}) matches your current knowledge level."
                )
            else:
                score -= 15.0

            # Relevance boost
            score += (primary_relevance * 20.0)

            # Assemble clean human-readable explanation
            full_explanation = " ".join(explanation_parts)

            scored_candidates.append({
                "content_item": item,
                "course": item.course,
                "score": round(score, 2),
                "reason_code": primary_reason,
                "explanation": full_explanation,
                "primary_skill": primary_skill,
                "current_mastery": current_mastery
            })

        # Sort descending by deterministic score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)

        # Select top-K
        selected = scored_candidates[:max_recommendations]

        results = []
        now = timezone.now()

        for idx, rec_data in enumerate(selected, start=1):
            rec_id = cls.generate_next_recommendation_id()
            rec_obj = Recommendation.objects.create(
                recommendation_id=rec_id,
                learner=learner,
                content_item=rec_data["content_item"],
                course=rec_data["course"],
                score=rec_data["score"],
                rank=idx,
                reason_code=rec_data["reason_code"],
                explanation=rec_data["explanation"],
                is_active=True,
                generated_at=now
            )

            results.append({
                "recommendation_id": rec_obj.recommendation_id,
                "rank": rec_obj.rank,
                "content_id": rec_data["content_item"].content_id,
                "title": rec_data["content_item"].title,
                "format": rec_data["content_item"].format,
                "difficulty": rec_data["content_item"].difficulty,
                "estimated_minutes": rec_data["content_item"].estimated_minutes,
                "course_id": rec_data["course"].course_id,
                "course_title": rec_data["course"].title,
                "score": rec_obj.score,
                "reason_code": rec_obj.reason_code,
                "explanation": rec_obj.explanation,
                "primary_skill": rec_data["primary_skill"].name if rec_data["primary_skill"] else None,
                "current_mastery": rec_data["current_mastery"]
            })

        AuditService.log_event(
            action="RECOMMENDATIONS_GENERATED",
            entity_type="Learner",
            entity_id=learner.learner_id,
            actor=actor or learner.user,
            details={
                "count": len(results),
                "top_recommendations": [r["content_id"] for r in results]
            },
            ip_address=ip_address
        )

        return results

    @classmethod
    def get_active_recommendations(cls, learner: Learner) -> List[Dict[str, Any]]:
        """
        Retrieves current active recommendations for a learner.
        If none exist, automatically generates fresh recommendations.
        """
        active_recs = Recommendation.objects.filter(
            learner=learner,
            is_active=True
        ).select_related('content_item', 'course').order_by('rank')

        if not active_recs.exists():
            return cls.generate_recommendations(learner)

        results = []
        for rec in active_recs:
            results.append({
                "recommendation_id": rec.recommendation_id,
                "rank": rec.rank,
                "content_id": rec.content_item.content_id,
                "title": rec.content_item.title,
                "format": rec.content_item.format,
                "difficulty": rec.content_item.difficulty,
                "estimated_minutes": rec.content_item.estimated_minutes,
                "course_id": rec.course.course_id,
                "course_title": rec.course.title,
                "score": rec.score,
                "reason_code": rec.reason_code,
                "explanation": rec.explanation,
                "generated_at": rec.generated_at.isoformat()
            })
        return results
