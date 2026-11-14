"""
Learning Path Service.
Generates ordered, acyclic learning paths for target courses or skills.
Manages step-by-step progress and handles prerequisite blocking.
"""

from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from learning_system.models import (
    Learner, Course, Skill, ContentItem, LearningPath,
    LearningPathItem, LearningPathStatus, LearningPathItemStatus,
    Attempt
)
from learning_system.services.prerequisite_service import PrerequisiteService
from learning_system.services.audit_service import AuditService


class LearningPathService:
    @staticmethod
    def generate_next_path_id() -> str:
        """
        Generates sequentially ordered ID: PATH-2026-000001
        """
        year = timezone.now().year
        count = LearningPath.objects.count() + 1
        while True:
            candidate_id = f"PATH-{year}-{count:06d}"
            if not LearningPath.objects.filter(path_id=candidate_id).exists():
                return candidate_id
            count += 1

    @classmethod
    @transaction.atomic
    def generate_path_for_course(cls, learner: Learner, course: Course, actor=None) -> LearningPath:
        """
        Generates an ordered learning path for a course.
        Resolves prerequisite courses first, then orders content items by prerequisite dependency.
        Guarantees no circular loops.
        """
        # Check if an active path already exists
        existing_path = LearningPath.objects.filter(
            learner=learner,
            target_course=course,
            status__in=[LearningPathStatus.CREATED, LearningPathStatus.IN_PROGRESS]
        ).first()

        if existing_path:
            return existing_path

        path_id = cls.generate_next_path_id()
        now = timezone.now()

        # Collect all content items needed:
        # If the course has prerequisites, include fundamental content first
        ordered_content_items: List[ContentItem] = []

        prereq_rules = course.prerequisite_rules.select_related('prerequisite_course').all()
        for rule in prereq_rules:
            prereq_items = list(rule.prerequisite_course.content_items.filter(is_active=True).order_by('order'))
            ordered_content_items.extend(prereq_items)

        # Then add target course content items
        target_items = list(course.content_items.filter(is_active=True).order_by('order'))
        ordered_content_items.extend(target_items)

        # Deduplicate while preserving topological order
        seen_ids = set()
        unique_items = []
        for item in ordered_content_items:
            if item.content_id not in seen_ids:
                seen_ids.add(item.content_id)
                unique_items.append(item)

        if not unique_items:
            raise ValidationError(f"Course '{course.title}' has no learning activities.")

        # Determine path status
        eligibility = PrerequisiteService.evaluate_course_eligibility(learner, course)
        initial_status = LearningPathStatus.IN_PROGRESS
        if course.is_advanced and not eligibility["is_eligible"]:
            initial_status = LearningPathStatus.IN_PROGRESS  # In progress as fundamental steps are being worked on

        path_obj = LearningPath.objects.create(
            path_id=path_id,
            learner=learner,
            target_course=course,
            status=initial_status,
            progress_percentage=0.0,
            created_at=now
        )

        # Find which items learner already completed
        passed_content_ids = set(Attempt.objects.filter(
            learner=learner,
            passed=True,
            is_valid=True,
            content_item__isnull=False
        ).values_list('content_item_id', flat=True))

        completed_count = 0
        for idx, item in enumerate(unique_items, start=1):
            is_comp = item.content_id in passed_content_ids
            item_status = LearningPathItemStatus.COMPLETED if is_comp else LearningPathItemStatus.PENDING

            if is_comp:
                completed_count += 1

            LearningPathItem.objects.create(
                learning_path=path_obj,
                content_item=item,
                order=idx,
                status=item_status,
                completed_at=now if is_comp else None
            )

        # Update initial progress
        if unique_items:
            path_obj.progress_percentage = round((completed_count / len(unique_items)) * 100.0, 1)
            if path_obj.progress_percentage >= 100.0:
                path_obj.status = LearningPathStatus.COMPLETED
                path_obj.completed_at = now
            path_obj.save(update_fields=['progress_percentage', 'status', 'completed_at'])

        AuditService.log_event(
            action="LEARNING_PATH_CREATED",
            entity_type="LearningPath",
            entity_id=path_obj.path_id,
            actor=actor or learner.user,
            details={
                "target_course": course.code,
                "total_steps": len(unique_items),
                "initial_progress": path_obj.progress_percentage
            }
        )

        return path_obj

    @classmethod
    def get_learner_path_details(cls, learner: Learner) -> Optional[Dict[str, Any]]:
        """
        Retrieves active learning path with step-by-step progress details.
        """
        path = LearningPath.objects.filter(
            learner=learner
        ).select_related('target_course', 'target_skill').order_by('-created_at').first()

        if not path:
            return None

        items = path.items.select_related('content_item', 'content_item__course').order_by('order')
        steps = []
        for it in items:
            steps.append({
                "order": it.order,
                "content_id": it.content_item.content_id,
                "title": it.content_item.title,
                "format": it.content_item.format,
                "difficulty": it.content_item.difficulty,
                "course_code": it.content_item.course.code,
                "course_title": it.content_item.course.title,
                "status": it.status,
                "completed_at": it.completed_at.isoformat() if it.completed_at else None
            })

        return {
            "path_id": path.path_id,
            "target_course_title": path.target_course.title if path.target_course else "Custom Goal",
            "target_course_code": path.target_course.code if path.target_course else None,
            "status": path.status,
            "progress_percentage": path.progress_percentage,
            "created_at": path.created_at.isoformat(),
            "completed_at": path.completed_at.isoformat() if path.completed_at else None,
            "steps": steps
        }
