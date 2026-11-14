"""
Core Database Models for Personalized Learning Recommendation System.
Defines entities for RBAC, Learners, Courses, Skills, Prerequisites,
Assessments, Attempts, Mastery, Recommendations, Learning Paths,
Support, Audit Logging, and Data Quality Tracking.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# -------------------------------------------------------------------------
# 1. USER & AUTHENTICATION (RBAC & REGISTRATION LIFECYCLE)
# -------------------------------------------------------------------------

class UserRole(models.TextChoices):
    STUDENT = 'STUDENT', 'Student'
    INSTRUCTOR = 'INSTRUCTOR', 'Instructor'
    ACADEMIC_ADMIN = 'ACADEMIC_ADMIN', 'Academic Administrator'
    SUPPORT_STAFF = 'SUPPORT_STAFF', 'Support Staff'
    PLATFORM_ADMIN = 'PLATFORM_ADMIN', 'Platform Administrator'

# Alias for backward compatibility
UserRole.LEARNER = UserRole.STUDENT


class AccountStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'


class User(AbstractUser):
    """
    Custom user model with explicit Role-Based Access Control (RBAC)
    and account lifecycle (Active / Suspended).
    """
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.role == UserRole.PLATFORM_ADMIN:
            existing = User.objects.filter(role=UserRole.PLATFORM_ADMIN)
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                from django.core.exceptions import ValidationError
                raise ValidationError("Only one Platform Administrator is permitted on the platform.")

    def is_student(self):
        return self.role in [UserRole.STUDENT, 'LEARNER']

    def is_learner(self):
        return self.is_student()

    def is_instructor(self):
        return self.role == UserRole.INSTRUCTOR

    def is_academic_admin(self):
        return self.role == UserRole.ACADEMIC_ADMIN

    def is_support_staff(self):
        return self.role == UserRole.SUPPORT_STAFF

    def is_platform_admin(self):
        return self.role == UserRole.PLATFORM_ADMIN or self.is_superuser

    def is_active_approved(self):
        return self.status == AccountStatus.ACTIVE and self.is_active

    def __str__(self):
        return f"{self.username} ({self.role} - {self.status})"


# -------------------------------------------------------------------------
# 2. LEARNER
# -------------------------------------------------------------------------

class Learner(models.Model):
    """
    Learner entity storing academic profile, goals, and history.
    """
    learner_id = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="Format: LRN-000001"
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='learner_profile'
    )
    current_education_level = models.CharField(
        max_length=50,
        default='UNDERGRADUATE'
    )
    learning_goals = models.TextField(blank=True, default='')
    total_completed_activities = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['learner_id']
        indexes = [
            models.Index(fields=['learner_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.learner_id} - {self.user.get_full_name() or self.user.username}"


# Alias Student to Learner
Student = Learner


# -------------------------------------------------------------------------
# 3. COURSES & COURSE PREREQUISITES
# -------------------------------------------------------------------------

class DifficultyLevel(models.TextChoices):
    BEGINNER = 'BEGINNER', 'Beginner'
    INTERMEDIATE = 'INTERMEDIATE', 'Intermediate'
    ADVANCED = 'ADVANCED', 'Advanced'


class Course(models.Model):
    """
    Educational courses. Can be fundamental or advanced with prerequisites.
    """
    course_id = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="Format: CRS-000001"
    )
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    difficulty = models.CharField(
        max_length=15,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.BEGINNER
    )
    is_advanced = models.BooleanField(
        default=False,
        help_text="Advanced courses require passing prerequisite courses and assessments."
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_courses'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['course_id']
        indexes = [
            models.Index(fields=['course_id']),
            models.Index(fields=['code']),
            models.Index(fields=['difficulty']),
        ]

    def __str__(self):
        return f"{self.course_id} [{self.code}] {self.title}"


class CoursePrerequisite(models.Model):
    """
    Gating relationship: A course requires completion of prerequisite course(s),
    minimum mastery in skills, and optionally passing a prerequisite assessment.
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='prerequisite_rules'
    )
    prerequisite_course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='unlocks_courses'
    )
    required_min_mastery = models.FloatField(
        default=70.0,
        help_text="Minimum skill mastery percentage required (0-100)"
    )
    required_assessment = models.ForeignKey(
        'Assessment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='required_for_course_prereqs'
    )
    min_score = models.FloatField(
        default=70.0,
        help_text="Minimum assessment score percentage required"
    )

    class Meta:
        unique_together = ('course', 'prerequisite_course')

    def __str__(self):
        return f"{self.course.code} requires {self.prerequisite_course.code} (>= {self.min_score}%)"


# -------------------------------------------------------------------------
# 4. SKILLS & SKILL PREREQUISITES
# -------------------------------------------------------------------------

class Skill(models.Model):
    """
    Granular skills tracked by the system.
    """
    skill_id = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="Format: SKL-000001"
    )
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['skill_id']
        indexes = [
            models.Index(fields=['skill_id']),
            models.Index(fields=['code']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.skill_id} - {self.name}"


class SkillPrerequisite(models.Model):
    """
    Directed Acyclic Graph (DAG) relationship between skills.
    parent_skill requires prerequisite_skill to be mastered first.
    """
    parent_skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='prerequisite_dependencies'
    )
    prerequisite_skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='unlocks_dependent_skills'
    )
    required_mastery_level = models.FloatField(default=70.0)

    class Meta:
        unique_together = ('parent_skill', 'prerequisite_skill')

    def __str__(self):
        return f"{self.parent_skill.code} requires {self.prerequisite_skill.code} (>= {self.required_mastery_level}%)"


# -------------------------------------------------------------------------
# 5. CONTENT ITEMS & CONTENT-SKILL MAPPING
# -------------------------------------------------------------------------

class ContentFormat(models.TextChoices):
    VIDEO = 'VIDEO', 'Video Lecture'
    ARTICLE = 'ARTICLE', 'Reading Material'
    EXERCISE = 'EXERCISE', 'Interactive Exercise'
    QUIZ = 'QUIZ', 'Assessment Quiz'


class ContentItem(models.Model):
    """
    Modular educational learning activity / material.
    """
    content_id = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="Format: CNT-000001"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='content_items'
    )
    title = models.CharField(max_length=250)
    format = models.CharField(
        max_length=15,
        choices=ContentFormat.choices,
        default=ContentFormat.ARTICLE
    )
    difficulty = models.CharField(
        max_length=15,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.BEGINNER
    )
    estimated_minutes = models.PositiveIntegerField(default=15)
    content_body = models.TextField(
        blank=True,
        default='',
        help_text="Text content, instructions, or media URL"
    )
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['course', 'order']
        indexes = [
            models.Index(fields=['content_id']),
            models.Index(fields=['course', 'order']),
            models.Index(fields=['difficulty']),
        ]

    def __str__(self):
        return f"{self.content_id}: {self.title} ({self.format} - {self.difficulty})"


class ContentSkill(models.Model):
    """
    Bridge table connecting educational content to skills with relevance weights.
    """
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name='skill_mappings'
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='content_mappings'
    )
    relevance_weight = models.FloatField(
        default=1.0,
        help_text="Relevance weight between 0.1 and 1.0"
    )

    class Meta:
        unique_together = ('content_item', 'skill')

    def __str__(self):
        return f"{self.content_item.content_id} -> {self.skill.code} (wt: {self.relevance_weight})"


# -------------------------------------------------------------------------
# 6. ENROLLMENTS & COURSE COMPLETION
# -------------------------------------------------------------------------

class EnrollmentStatus(models.TextChoices):
    ENROLLED = 'ENROLLED', 'Enrolled'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    DROPPED = 'DROPPED', 'Dropped'


class CourseEnrollment(models.Model):
    """
    Learner enrollment in a course.
    """
    learner = models.ForeignKey(
        Learner,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    status = models.CharField(
        max_length=15,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED
    )
    progress_percentage = models.FloatField(default=0.0)
    enrolled_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('learner', 'course')
        indexes = [
            models.Index(fields=['learner', 'course']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.learner.learner_id} in {self.course.code} [{self.status}]"


# -------------------------------------------------------------------------
# 7. ASSESSMENTS, QUESTIONS & ATTEMPTS
# -------------------------------------------------------------------------

class Assessment(models.Model):
    """
    Assessment or quiz entity. Can serve as a prerequisite gating exam.
    """
    assessment_id = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="Format: ASM-000001"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='assessments'
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='assessments',
        help_text="Target skill evaluated by this assessment"
    )
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='associated_assessments'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    passing_percentage = models.FloatField(default=70.0)
    is_prerequisite_gate = models.BooleanField(
        default=False,
        help_text="If True, passing this assessment is required to unlock advanced courses."
    )
    time_limit_minutes = models.PositiveIntegerField(default=30)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['assessment_id']
        indexes = [
            models.Index(fields=['assessment_id']),
            models.Index(fields=['course']),
            models.Index(fields=['skill']),
        ]

    def __str__(self):
        return f"{self.assessment_id}: {self.title} (Pass: {self.passing_percentage}%)"


class QuestionType(models.TextChoices):
    MULTIPLE_CHOICE = 'MULTIPLE_CHOICE', 'Multiple Choice'
    TRUE_FALSE = 'TRUE_FALSE', 'True / False'
    SINGLE_CHOICE = 'SINGLE_CHOICE', 'Single Choice'


class AssessmentQuestion(models.Model):
    """
    Question within an assessment. Contains options and verified answer.
    """
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.MULTIPLE_CHOICE
    )
    options_json = models.JSONField(
        default=list,
        help_text="List of choices: [{'key': 'A', 'text': 'Option A'}, ...]"
    )
    correct_answer = models.CharField(
        max_length=50,
        help_text="Option key corresponding to correct answer, e.g. 'A'"
    )
    points = models.FloatField(default=1.0)
    explanation = models.TextField(blank=True, default='')
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['assessment', 'order']

    def __str__(self):
        return f"Q{self.order} for {self.assessment.assessment_id}: {self.question_text[:50]}"


class Attempt(models.Model):
    """
    Historical record of an assessment attempt by a learner.
    Preserves full immutability of historical performance.
    """
    attempt_id = models.CharField(
        max_length=50,
        primary_key=True,
        help_text="Format: ATT-<learner-id>-000001"
    )
    learner = models.ForeignKey(
        Learner,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_attempts'
    )
    attempt_number = models.PositiveIntegerField(default=1)
    score = models.FloatField(default=0.0)
    max_score = models.FloatField(default=100.0)
    percentage = models.FloatField(default=0.0)
    passed = models.BooleanField(default=False)
    is_valid = models.BooleanField(
        default=True,
        help_text="Set to False if flagged by validation rules or anomaly tests"
    )
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['learner', 'attempt_number']
        indexes = [
            models.Index(fields=['attempt_id']),
            models.Index(fields=['learner', 'assessment']),
            models.Index(fields=['completed_at']),
        ]

    def __str__(self):
        return f"{self.attempt_id} - Score: {self.percentage:.1f}% ({'PASS' if self.passed else 'FAIL'})"


class AssessmentResponse(models.Model):
    """
    Individual question response within an attempt.
    """
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    question = models.ForeignKey(
        AssessmentQuestion,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    selected_option = models.CharField(max_length=50)
    is_correct = models.BooleanField(default=False)
    points_earned = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('attempt', 'question')

    def __str__(self):
        return f"{self.attempt.attempt_id} Q:{self.question.id} -> {'Correct' if self.is_correct else 'Incorrect'}"


class AssessmentResult(models.Model):
    """
    Processed result and feedback for an assessment attempt.
    """
    attempt = models.OneToOneField(
        Attempt,
        on_delete=models.CASCADE,
        related_name='result'
    )
    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField()
    score_percentage = models.FloatField()
    passed = models.BooleanField()
    feedback = models.TextField(blank=True, default='')
    computed_mastery_impact = models.JSONField(
        default=dict,
        help_text="Details of how this result influenced skill mastery"
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Result {self.attempt.attempt_id}: {self.score_percentage:.1f}%"


# -------------------------------------------------------------------------
# 8. SKILL MASTERY & MASTERY HISTORY
# -------------------------------------------------------------------------

class MasteryLevel(models.TextChoices):
    NEEDS_IMPROVEMENT = 'NEEDS_IMPROVEMENT', 'Needs Improvement (<40%)'
    DEVELOPING = 'DEVELOPING', 'Developing (40-69%)'
    PROFICIENT = 'PROFICIENT', 'Proficient (70-84%)'
    MASTERED = 'MASTERED', 'Mastered (85-100%)'


class SkillMastery(models.Model):
    """
    Current computed mastery level for a learner in a specific skill.
    """
    learner = models.ForeignKey(
        Learner,
        on_delete=models.CASCADE,
        related_name='skill_masteries'
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='learner_masteries'
    )
    mastery_percentage = models.FloatField(default=0.0)
    mastery_level = models.CharField(
        max_length=20,
        choices=MasteryLevel.choices,
        default=MasteryLevel.NEEDS_IMPROVEMENT
    )
    attempt_count = models.PositiveIntegerField(default=0)
    calculated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('learner', 'skill')
        indexes = [
            models.Index(fields=['learner', 'skill']),
            models.Index(fields=['mastery_level']),
        ]

    def __str__(self):
        return f"{self.learner.learner_id} - {self.skill.code}: {self.mastery_percentage:.1f}% ({self.mastery_level})"


class SkillMasteryHistory(models.Model):
    """
    Immutable temporal history of skill mastery calculations to prevent future leakage
    and provide full reproducibility.
    """
    learner = models.ForeignKey(
        Learner,
        on_delete=models.CASCADE,
        related_name='mastery_history'
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='mastery_history'
    )
    mastery_percentage = models.FloatField()
    mastery_level = models.CharField(max_length=20, choices=MasteryLevel.choices)
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mastery_history_triggers'
    )
    calculated_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['calculated_at']

    def __str__(self):
        return f"{self.learner.learner_id} {self.skill.code} @ {self.calculated_at}: {self.mastery_percentage:.1f}%"


# -------------------------------------------------------------------------
# 9. RECOMMENDATIONS & OUTCOMES
# -------------------------------------------------------------------------

class RecommendationReasonCode(models.TextChoices):
    SKILL_GAP = 'SKILL_GAP', 'Skill Gap Detected (<70% mastery)'
    PREREQUISITES_MET = 'PREREQUISITES_MET', 'Prerequisites Fully Satisfied'
    PREREQUISITES_NOT_MET = 'PREREQUISITES_NOT_MET', 'Prerequisites Missing - Revision Required'
    DIFFICULTY_MATCH = 'DIFFICULTY_MATCH', 'Content Matches Current Mastery Level'
    DIFFICULTY_MISMATCH = 'DIFFICULTY_MISMATCH', 'Content Level Mismatch'
    NOT_COMPLETED = 'NOT_COMPLETED', 'Activity Not Yet Completed'
    ASSESSMENT_FAILED = 'ASSESSMENT_FAILED', 'Targeted Revision for Recent Failed Assessment'
    COLD_START = 'COLD_START', 'Cold Start Onboarding Activity'


class Recommendation(models.Model):
    """
    Deterministic explainable recommendation entity.
    """
    recommendation_id = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="Format: REC-000001"
    )
    learner = models.ForeignKey(
        Learner,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    score = models.FloatField(
        default=0.0,
        help_text="Deterministic ranking score computed by recommendation engine"
    )
    rank = models.PositiveIntegerField(default=1)
    reason_code = models.CharField(
        max_length=30,
        choices=RecommendationReasonCode.choices,
        default=RecommendationReasonCode.SKILL_GAP
    )
    explanation = models.TextField(
        help_text="Human-readable explanation of why this activity was recommended"
    )
    is_active = models.BooleanField(default=True)
    generated_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['rank', '-score']
        indexes = [
            models.Index(fields=['learner', 'is_active']),
            models.Index(fields=['generated_at']),
        ]

    def __str__(self):
        return f"{self.recommendation_id} for {self.learner.learner_id}: {self.content_item.title} ({self.reason_code})"


class RecommendationOutcome(models.Model):
    """
    Subsequent learner interaction and performance tracking following a recommendation.
    """
    recommendation = models.ForeignKey(
        Recommendation,
        on_delete=models.CASCADE,
        related_name='outcomes'
    )
    learner = models.ForeignKey(
        Learner,
        on_delete=models.CASCADE,
        related_name='recommendation_outcomes'
    )
    clicked = models.BooleanField(default=False)
    started = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Optional learner rating 1-5"
    )
    score_achieved = models.FloatField(
        null=True,
        blank=True,
        help_text="Score achieved on subsequent assessment attempt"
    )
    recorded_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Outcome for {self.recommendation.recommendation_id}: Completed={self.completed}"


# -------------------------------------------------------------------------
# 10. LEARNING PATHS & PATH ITEMS
# -------------------------------------------------------------------------

class LearningPathStatus(models.TextChoices):
    CREATED = 'CREATED', 'Created'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    BLOCKED = 'BLOCKED', 'Blocked (Prerequisite Unmet)'
    CANCELLED = 'CANCELLED', 'Cancelled'


class LearningPath(models.Model):
    """
    Personalized sequence of learning activities targeting a skill or course goal.
    Guaranteed Directed Acyclic Graph (DAG) with no circular loops.
    """
    path_id = models.CharField(
        max_length=30,
        primary_key=True,
        help_text="Format: PATH-2026-000001"
    )
    learner = models.ForeignKey(
        Learner,
        on_delete=models.CASCADE,
        related_name='learning_paths'
    )
    target_course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='targeted_by_paths'
    )
    target_skill = models.ForeignKey(
        Skill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='targeted_by_paths'
    )
    status = models.CharField(
        max_length=20,
        choices=LearningPathStatus.choices,
        default=LearningPathStatus.CREATED
    )
    progress_percentage = models.FloatField(default=0.0)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['path_id']),
            models.Index(fields=['learner', 'status']),
        ]

    def __str__(self):
        return f"{self.path_id} for {self.learner.learner_id} [{self.status}]"


class LearningPathItemStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    BLOCKED = 'BLOCKED', 'Blocked'


class LearningPathItem(models.Model):
    """
    Ordered step in a learning path.
    """
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.CASCADE,
        related_name='items'
    )
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name='path_assignments'
    )
    order = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=15,
        choices=LearningPathItemStatus.choices,
        default=LearningPathItemStatus.PENDING
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['learning_path', 'order']
        unique_together = ('learning_path', 'content_item')

    def __str__(self):
        return f"{self.learning_path.path_id} Step {self.order}: {self.content_item.title}"


# -------------------------------------------------------------------------
# 11. SUPPORT TICKETS & AUDIT LOGS
# -------------------------------------------------------------------------

class TicketCategory(models.TextChoices):
    LOGIN = 'LOGIN', 'Login Problem'
    ASSESSMENT = 'ASSESSMENT', 'Assessment Submission Issue'
    RECOMMENDATION = 'RECOMMENDATION', 'Incorrect Recommendation'
    CONTENT = 'CONTENT', 'Content or Material Issue'
    PREREQUISITE = 'PREREQUISITE', 'Course Prerequisite Lock Query'
    OTHER = 'OTHER', 'General Support'


class TicketStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    RESOLVED = 'RESOLVED', 'Resolved'
    ESCALATED = 'ESCALATED', 'Escalated to Platform Admin'


class SupportTicket(models.Model):
    """
    Support ticket for learner issues, investigated by Support Staff.
    """
    ticket_id = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="Format: TCK-000001"
    )
    learner = models.ForeignKey(
        Learner,
        on_delete=models.CASCADE,
        related_name='support_tickets'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets'
    )
    category = models.CharField(
        max_length=20,
        choices=TicketCategory.choices,
        default=TicketCategory.OTHER
    )
    status = models.CharField(
        max_length=20,
        choices=TicketStatus.choices,
        default=TicketStatus.OPEN
    )
    subject = models.CharField(max_length=250)
    description = models.TextField()
    resolution = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket_id} [{self.category} - {self.status}]: {self.subject}"


class AuditLog(models.Model):
    """
    System-wide audit trail for compliance, security events, and traceability.
    """
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions'
    )
    action = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50)
    details_json = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor_name = self.actor.username if self.actor else "SYSTEM"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {actor_name} -> {self.action} on {self.entity_type}:{self.entity_id}"


# -------------------------------------------------------------------------
# 12. DATA GENERATION RUNS & ANOMALIES (DATA QUALITY TRACKING)
# -------------------------------------------------------------------------

class GenerationMode(models.TextChoices):
    STARTER = 'STARTER', 'Starter (100 Learners, 30 Skills, 50 Content, 1000 Attempts)'
    FULL = 'FULL', 'Full (10,000 Learners, 500 Skills, 2,000 Content, 500,000 Attempts)'


class DataGenerationRun(models.Model):
    """
    Tracks synthetic data generation executions and reproducibility.
    """
    seed = models.BigIntegerField(default=20261022)
    mode = models.CharField(
        max_length=15,
        choices=GenerationMode.choices,
        default=GenerationMode.STARTER
    )
    learner_count = models.PositiveIntegerField(default=0)
    skill_count = models.PositiveIntegerField(default=0)
    content_count = models.PositiveIntegerField(default=0)
    attempt_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='IN_PROGRESS')
    summary_report = models.JSONField(default=dict)

    def __str__(self):
        return f"DataGenRun #{self.id} [{self.mode} - Seed: {self.seed}] - {self.status}"


class AnomalyType(models.TextChoices):
    PREREQUISITE_VIOLATION = 'PREREQUISITE_VIOLATION', 'Recommendation violates course prerequisite'
    INVALID_TIMESTAMP_ORDER = 'INVALID_TIMESTAMP_ORDER', 'Attempt completion timestamp earlier than start time'
    NONEXISTENT_SKILL_MAPPING = 'NONEXISTENT_SKILL_MAPPING', 'Content mapped to nonexistent skill ID'
    FUTURE_ATTEMPT_LEAKAGE = 'FUTURE_ATTEMPT_LEAKAGE', 'Mastery calculation uses a future attempt timestamp'
    LEARNING_PATH_LOOP = 'LEARNING_PATH_LOOP', 'Learning path contains circular loop without progress'


class DataQualityIssue(models.Model):
    """
    Injected or detected anomalies for validation and data quality benchmarking.
    Labels are isolated and NEVER used as input features for recommendation engine.
    """
    issue_id = models.CharField(max_length=30, primary_key=True)
    issue_type = models.CharField(max_length=40, choices=AnomalyType.choices)
    related_entity_id = models.CharField(max_length=50)
    ground_truth_label = models.CharField(
        max_length=50,
        help_text="Ground-truth anomaly classification (isolated from production engine)"
    )
    expected_decision = models.CharField(max_length=100)
    actual_decision = models.CharField(max_length=100, blank=True, default='')
    validation_result = models.CharField(
        max_length=20,
        default='DETECTED',
        help_text="DETECTED, MISSED, or RESOLVED"
    )
    details_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.issue_id} [{self.issue_type}]: {self.ground_truth_label} on {self.related_entity_id}"
