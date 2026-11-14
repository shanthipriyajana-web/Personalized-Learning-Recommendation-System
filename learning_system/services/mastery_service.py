"""
Skill Mastery Calculation Service.
Calculates reproducible, explainable skill mastery from historical valid attempts.
Maintains an immutable temporal audit log of mastery calculations.
"""

from typing import Dict, Any, List
from django.conf import settings
from django.utils import timezone
from learning_system.models import (
    Learner, Skill, Attempt, SkillMastery, SkillMasteryHistory,
    MasteryLevel, ContentSkill
)


class MasteryService:
    @staticmethod
    def get_mastery_level_for_percentage(percentage: float) -> str:
        """
        Classifies percentage into configurable mastery tiers:
        <40% -> NEEDS_IMPROVEMENT
        40-69% -> DEVELOPING
        70-84% -> PROFICIENT
        >=85% -> MASTERED
        """
        thresholds = getattr(settings, 'MASTERY_THRESHOLDS', {
            'NEEDS_IMPROVEMENT': 40.0,
            'DEVELOPING': 70.0,
            'PROFICIENT': 85.0
        })

        if percentage < thresholds['NEEDS_IMPROVEMENT']:
            return MasteryLevel.NEEDS_IMPROVEMENT
        elif percentage < thresholds['DEVELOPING']:
            return MasteryLevel.DEVELOPING
        elif percentage < thresholds['PROFICIENT']:
            return MasteryLevel.PROFICIENT
        else:
            return MasteryLevel.MASTERED

    @classmethod
    def calculate_skill_mastery(cls, learner: Learner, skill: Skill,
                                as_of_time=None, trigger_attempt: Attempt = None) -> SkillMastery:
        """
        Calculates deterministic skill mastery from valid past attempts.
        Mastery = (Sum of valid assessment scores) / (Number of valid attempts).
        Supports temporal calculation ('as_of_time') to prevent future leakage in evaluations.
        """
        # Find all assessments mapped directly to this skill, or content items linked to this skill
        valid_attempts_query = Attempt.objects.filter(
            learner=learner,
            is_valid=True
        ).filter(
            models_or_assessment_skill(skill)
        )

        if as_of_time:
            valid_attempts_query = valid_attempts_query.filter(completed_at__lte=as_of_time)

        attempts_list = list(valid_attempts_query.order_by('completed_at'))
        attempt_count = len(attempts_list)

        if attempt_count == 0:
            percentage = 0.0
            level = MasteryLevel.NEEDS_IMPROVEMENT
        else:
            # Deterministic calculation: average of valid percentage scores
            total_score = sum(att.percentage for att in attempts_list)
            percentage = round(total_score / attempt_count, 2)
            level = cls.get_mastery_level_for_percentage(percentage)

        calc_time = as_of_time or timezone.now()

        # Update or create the current SkillMastery snapshot
        mastery_obj, _ = SkillMastery.objects.update_or_create(
            learner=learner,
            skill=skill,
            defaults={
                'mastery_percentage': percentage,
                'mastery_level': level,
                'attempt_count': attempt_count,
                'calculated_at': calc_time
            }
        )

        # Record immutable history for temporal traceability
        SkillMasteryHistory.objects.create(
            learner=learner,
            skill=skill,
            mastery_percentage=percentage,
            mastery_level=level,
            attempt=trigger_attempt,
            calculated_at=calc_time
        )

        return mastery_obj

    @classmethod
    def get_learner_mastery_summary(cls, learner: Learner) -> List[Dict[str, Any]]:
        """
        Returns full mastery breakdown for all skills relevant to learner's courses.
        """
        masteries = SkillMastery.objects.filter(
            learner=learner
        ).select_related('skill').order_by('skill__name')

        result = []
        for m in masteries:
            result.append({
                "skill_id": m.skill.skill_id,
                "skill_name": m.skill.name,
                "skill_code": m.skill.code,
                "category": m.skill.category,
                "mastery_percentage": m.mastery_percentage,
                "mastery_level": m.mastery_level,
                "mastery_display": m.get_mastery_level_display(),
                "attempt_count": m.attempt_count,
                "calculated_at": m.calculated_at.isoformat()
            })
        return result


def models_or_assessment_skill(skill: Skill):
    """
    Constructs a Q filter matching attempts whose assessment or content item maps to the skill.
    """
    from django.db.models import Q
    return (
        Q(assessment__skill=skill) |
        Q(content_item__skill_mappings__skill=skill)
    )
