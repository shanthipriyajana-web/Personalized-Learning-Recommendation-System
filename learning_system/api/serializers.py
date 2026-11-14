"""
REST API Serializers.
Provides input validation, serialization and deserialization for all entities.
"""

from rest_framework import serializers
from learning_system.models import (
    User, UserRole, AccountStatus, Learner, Course, CoursePrerequisite,
    Skill, SkillPrerequisite, ContentItem, ContentSkill, CourseEnrollment,
    Assessment, AssessmentQuestion, Attempt, AssessmentResponse,
    AssessmentResult, SkillMastery, Recommendation, LearningPath,
    LearningPathItem, SupportTicket, RegistrationApproval, DataQualityIssue
)


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'status']


class LearnerProfileSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = Learner
        fields = [
            'learner_id', 'user', 'current_education_level',
            'learning_goals', 'total_completed_activities',
            'created_at', 'updated_at'
        ]


class LearnerRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    education_level = serializers.CharField(max_length=50, default='UNDERGRADUATE')
    learning_goals = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class RegistrationApprovalSerializer(serializers.ModelSerializer):
    learner_id = serializers.CharField(source='learner.learner_id', read_only=True)
    username = serializers.CharField(source='learner.user.username', read_only=True)
    email = serializers.CharField(source='learner.user.email', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)

    class Meta:
        model = RegistrationApproval
        fields = [
            'approval_id', 'learner_id', 'username', 'email',
            'reviewed_by_name', 'decision', 'reason', 'created_at'
        ]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['skill_id', 'name', 'code', 'category', 'description', 'created_at']


class SkillPrerequisiteSerializer(serializers.ModelSerializer):
    parent_skill_name = serializers.CharField(source='parent_skill.name', read_only=True)
    prerequisite_skill_name = serializers.CharField(source='prerequisite_skill.name', read_only=True)

    class Meta:
        model = SkillPrerequisite
        fields = [
            'id', 'parent_skill', 'parent_skill_name',
            'prerequisite_skill', 'prerequisite_skill_name',
            'required_mastery_level'
        ]


class CoursePrerequisiteSerializer(serializers.ModelSerializer):
    prerequisite_course_code = serializers.CharField(source='prerequisite_course.code', read_only=True)
    prerequisite_course_title = serializers.CharField(source='prerequisite_course.title', read_only=True)

    class Meta:
        model = CoursePrerequisite
        fields = [
            'id', 'course', 'prerequisite_course', 'prerequisite_course_code',
            'prerequisite_course_title', 'required_min_mastery',
            'required_assessment', 'min_score'
        ]


class ContentSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    skill_code = serializers.CharField(source='skill.code', read_only=True)

    class Meta:
        model = ContentSkill
        fields = ['id', 'skill', 'skill_name', 'skill_code', 'relevance_weight']


class ContentItemSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    skill_mappings = ContentSkillSerializer(many=True, read_only=True)

    class Meta:
        model = ContentItem
        fields = [
            'content_id', 'course', 'course_title', 'course_code',
            'title', 'format', 'difficulty', 'estimated_minutes',
            'content_body', 'order', 'is_active', 'skill_mappings', 'created_at'
        ]


class CourseSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    prerequisites = CoursePrerequisiteSerializer(source='prerequisite_rules', many=True, read_only=True)
    content_count = serializers.IntegerField(source='content_items.count', read_only=True)

    class Meta:
        model = Course
        fields = [
            'course_id', 'title', 'code', 'description', 'difficulty',
            'is_advanced', 'created_by', 'created_by_name', 'is_active',
            'content_count', 'prerequisites', 'created_at'
        ]


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    course_difficulty = serializers.CharField(source='course.difficulty', read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = [
            'id', 'learner', 'course', 'course_title', 'course_code',
            'course_difficulty', 'status', 'progress_percentage',
            'enrolled_at', 'completed_at'
        ]


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = [
            'id', 'question_text', 'question_type', 'options_json',
            'points', 'order'
        ]
        # Notice: correct_answer and explanation omitted during assessment attempt taking for security!


class AssessmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    questions = AssessmentQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Assessment
        fields = [
            'assessment_id', 'course', 'course_title', 'skill',
            'skill_name', 'title', 'description', 'passing_percentage',
            'is_prerequisite_gate', 'time_limit_minutes', 'questions', 'created_at'
        ]


class AttemptSerializer(serializers.ModelSerializer):
    assessment_title = serializers.CharField(source='assessment.title', read_only=True)

    class Meta:
        model = Attempt
        fields = [
            'attempt_id', 'learner', 'assessment', 'assessment_title',
            'attempt_number', 'score', 'max_score', 'percentage',
            'passed', 'is_valid', 'started_at', 'completed_at'
        ]


class SkillMasterySerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    skill_code = serializers.CharField(source='skill.code', read_only=True)
    category = serializers.CharField(source='skill.category', read_only=True)

    class Meta:
        model = SkillMastery
        fields = [
            'id', 'skill', 'skill_name', 'skill_code', 'category',
            'mastery_percentage', 'mastery_level', 'attempt_count',
            'calculated_at'
        ]


class RecommendationSerializer(serializers.ModelSerializer):
    content_title = serializers.CharField(source='content_item.title', read_only=True)
    content_format = serializers.CharField(source='content_item.format', read_only=True)
    content_difficulty = serializers.CharField(source='content_item.difficulty', read_only=True)
    estimated_minutes = serializers.IntegerField(source='content_item.estimated_minutes', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)

    class Meta:
        model = Recommendation
        fields = [
            'recommendation_id', 'learner', 'content_item', 'content_title',
            'content_format', 'content_difficulty', 'estimated_minutes',
            'course', 'course_title', 'course_code', 'score', 'rank',
            'reason_code', 'explanation', 'is_active', 'generated_at'
        ]


class LearningPathItemSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='content_item.title', read_only=True)
    format = serializers.CharField(source='content_item.format', read_only=True)
    difficulty = serializers.CharField(source='content_item.difficulty', read_only=True)
    course_code = serializers.CharField(source='content_item.course.code', read_only=True)

    class Meta:
        model = LearningPathItem
        fields = [
            'id', 'content_item', 'title', 'format', 'difficulty',
            'course_code', 'order', 'status', 'completed_at'
        ]


class LearningPathSerializer(serializers.ModelSerializer):
    target_course_title = serializers.CharField(source='target_course.title', read_only=True)
    items = LearningPathItemSerializer(many=True, read_only=True)

    class Meta:
        model = LearningPath
        fields = [
            'path_id', 'learner', 'target_course', 'target_course_title',
            'target_skill', 'status', 'progress_percentage',
            'items', 'created_at', 'completed_at'
        ]


class SupportTicketSerializer(serializers.ModelSerializer):
    learner_id = serializers.CharField(source='learner.learner_id', read_only=True)
    learner_username = serializers.CharField(source='learner.user.username', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'ticket_id', 'learner', 'learner_id', 'learner_username',
            'assigned_to', 'assigned_to_name', 'category', 'status',
            'subject', 'description', 'resolution', 'created_at', 'updated_at'
        ]


class DataQualityIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataQualityIssue
        fields = '__all__'
