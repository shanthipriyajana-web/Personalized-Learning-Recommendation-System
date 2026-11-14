"""
Prerequisite Verification & Gating Service.
Enforces course access prerequisites, skill mastery requirements,
and prerequisite assessment gating rules on the backend.
"""

from typing import Dict, Any, List, Tuple
from django.conf import settings
from learning_system.models import (
    Learner, Course, CoursePrerequisite, CourseEnrollment,
    EnrollmentStatus, Attempt, Assessment, Skill, SkillPrerequisite,
    SkillMastery, MasteryLevel
)


class PrerequisiteService:
    @staticmethod
    def evaluate_course_eligibility(learner: Learner, course: Course) -> Dict[str, Any]:
        """
        Determines whether a learner is eligible to enroll in or access an advanced course.
        Enforces:
        1. Fundamental course completion.
        2. Required skill mastery percentages.
        3. Prerequisite assessment passing marks (>= 70%).

        Returns a detailed report explaining eligibility decisions and prerequisite rules.
        """
        if not course.is_advanced:
            return {
                "course_id": course.course_id,
                "course_title": course.title,
                "is_advanced": False,
                "is_eligible": True,
                "can_attempt_gating_assessment": True,
                "reasons": ["Fundamental course: open for enrollment."],
                "prerequisites_status": []
            }

        prerequisite_rules = CoursePrerequisite.objects.filter(
            course=course
        ).select_related('prerequisite_course', 'required_assessment')

        if not prerequisite_rules.exists():
            # If marked advanced but no rules defined, treat as eligible
            return {
                "course_id": course.course_id,
                "course_title": course.title,
                "is_advanced": True,
                "is_eligible": True,
                "can_attempt_gating_assessment": True,
                "reasons": ["No specific prerequisite rules configured."],
                "prerequisites_status": []
            }

        all_rules_satisfied = True
        can_attempt_assessment = True
        reasons = []
        rules_report = []

        for rule in prerequisite_rules:
            prereq_course = rule.prerequisite_course
            rule_passed = True
            rule_failure_reasons = []

            # 1. Check Course Completion
            enrollment = CourseEnrollment.objects.filter(
                learner=learner,
                course=prereq_course
            ).first()

            is_course_completed = False
            if enrollment and (enrollment.status == EnrollmentStatus.COMPLETED or enrollment.progress_percentage >= 100.0):
                is_course_completed = True
            else:
                rule_passed = False
                rule_failure_reasons.append(
                    f"Must complete fundamental course '{prereq_course.title}' [{prereq_course.code}]."
                )

            # 2. Check Skill Mastery for Skills related to prerequisite course
            skills_in_prereq = Skill.objects.filter(
                content_mappings__content_item__course=prereq_course
            ).distinct()

            skills_mastery_report = []
            skill_mastery_met = True

            for skl in skills_in_prereq:
                mastery_obj = SkillMastery.objects.filter(
                    learner=learner,
                    skill=skl
                ).first()

                current_pct = mastery_obj.mastery_percentage if mastery_obj else 0.0
                is_met = current_pct >= rule.required_min_mastery
                if not is_met:
                    skill_mastery_met = False
                    rule_passed = False
                    rule_failure_reasons.append(
                        f"Skill '{skl.name}' mastery is {current_pct:.1f}%, required is {rule.required_min_mastery:.1f}%."
                    )
                skills_mastery_report.append({
                    "skill_id": skl.skill_id,
                    "skill_name": skl.name,
                    "current_mastery": current_pct,
                    "required_mastery": rule.required_min_mastery,
                    "is_met": is_met
                })

            # Fundamental courses + skill mastery determine if prerequisite assessment can be taken
            if not is_course_completed or not skill_mastery_met:
                can_attempt_assessment = False

            # 3. Check Prerequisite Gating Assessment
            assessment_passed = True
            assessment_score = 0.0
            gating_assessment_info = None

            if rule.required_assessment:
                gating_assessment = rule.required_assessment
                best_attempt = Attempt.objects.filter(
                    learner=learner,
                    assessment=gating_assessment,
                    is_valid=True
                ).order_by('-percentage').first()

                if best_attempt and best_attempt.percentage >= rule.min_score:
                    assessment_passed = True
                    assessment_score = best_attempt.percentage
                else:
                    assessment_passed = False
                    rule_passed = False
                    score_str = f"{best_attempt.percentage:.1f}%" if best_attempt else "No attempts"
                    rule_failure_reasons.append(
                        f"Prerequisite assessment '{gating_assessment.title}' requires min score of {rule.min_score:.1f}% (current best: {score_str})."
                    )

                gating_assessment_info = {
                    "assessment_id": gating_assessment.assessment_id,
                    "title": gating_assessment.title,
                    "required_score": rule.min_score,
                    "best_score": assessment_score if best_attempt else None,
                    "passed": assessment_passed,
                    "can_attempt_now": can_attempt_assessment
                }

            if not rule_passed:
                all_rules_satisfied = False
                reasons.extend(rule_failure_reasons)

            rules_report.append({
                "prerequisite_course_id": prereq_course.course_id,
                "prerequisite_course_title": prereq_course.title,
                "is_course_completed": is_course_completed,
                "skill_masteries": skills_mastery_report,
                "gating_assessment": gating_assessment_info,
                "is_rule_satisfied": rule_passed
            })

        if all_rules_satisfied:
            reasons.append("All prerequisites and gating assessments have been fully satisfied. Course unlocked.")

        return {
            "course_id": course.course_id,
            "course_title": course.title,
            "is_advanced": True,
            "is_eligible": all_rules_satisfied,
            "can_attempt_gating_assessment": can_attempt_assessment,
            "reasons": reasons,
            "prerequisites_status": rules_report
        }

    @staticmethod
    def detect_skill_cycles() -> List[List[str]]:
        """
        Detects circular dependencies in the SkillPrerequisite graph using DFS cycle detection.
        Returns a list of cycle paths if any exist.
        """
        adjacency: Dict[str, List[str]] = {}
        for edge in SkillPrerequisite.objects.all():
            parent = edge.parent_skill.skill_id
            prereq = edge.prerequisite_skill.skill_id
            adjacency.setdefault(parent, []).append(prereq)

        cycles = []
        visited = {}  # 0: unvisited, 1: visiting, 2: visited
        current_path = []

        def dfs(node: str):
            visited[node] = 1
            current_path.append(node)

            for neighbor in adjacency.get(node, []):
                if visited.get(neighbor, 0) == 1:
                    # Cycle detected
                    idx = current_path.index(neighbor)
                    cycles.append(current_path[idx:] + [neighbor])
                elif visited.get(neighbor, 0) == 0:
                    dfs(neighbor)

            current_path.pop()
            visited[node] = 2

        all_nodes = set(adjacency.keys())
        for n in all_nodes:
            if visited.get(n, 0) == 0:
                dfs(n)

        return cycles
