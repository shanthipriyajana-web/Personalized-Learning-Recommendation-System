"""
RESTful API Views implementing the business logic, RBAC,
prerequisite gating, and recommendation endpoints.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login, logout
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError, PermissionDenied

from learning_system.models import (
    User, UserRole, AccountStatus, Learner, Course, Skill,
    ContentItem, ContentSkill, CourseEnrollment, EnrollmentStatus,
    Assessment, AssessmentQuestion, Attempt, SkillMastery, Recommendation, LearningPath,
    SupportTicket, RegistrationApproval, SkillPrerequisite,
    CoursePrerequisite, DataQualityIssue
)
from learning_system.services import (
    AuthService, PrerequisiteService, AssessmentService,
    MasteryService, RecommendationService, LearningPathService,
    ValidationService
)
from learning_system.api.permissions import (
    IsLearner, IsInstructor, IsAcademicAdmin, IsSupportStaff,
    IsPlatformAdmin, IsActiveApprovedUser
)
from learning_system.api.serializers import (
    UserSummarySerializer, LearnerProfileSerializer,
    LearnerRegistrationSerializer, LoginSerializer,
    RegistrationApprovalSerializer, SkillSerializer,
    CourseSerializer, ContentItemSerializer, AssessmentSerializer,
    AttemptSerializer, SkillMasterySerializer, RecommendationSerializer,
    LearningPathSerializer, SupportTicketSerializer, DataQualityIssueSerializer
)


# -------------------------------------------------------------------------
# AUTHENTICATION & APPROVAL VIEWS
# -------------------------------------------------------------------------

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LearnerRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        learner = AuthService.register_learner(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            education_level=data.get('education_level', 'UNDERGRADUATE'),
            learning_goals=data.get('learning_goals', ''),
            phone_number=data.get('phone_number', ''),
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response({
            "success": True,
            "message": "Registration submitted successfully. Your account is PENDING approval by a Platform Administrator.",
            "learner_id": learner.learner_id,
            "username": learner.user.username,
            "status": learner.user.status
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = AuthService.authenticate_with_status_check(username, password)
        login(request, user)

        learner_id = None
        if hasattr(user, 'learner_profile'):
            learner_id = user.learner_profile.learner_id

        return Response({
            "success": True,
            "message": f"Welcome back, {user.first_name or user.username}!",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "status": user.status,
                "learner_id": learner_id
            }
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({
            "success": True,
            "message": "Successfully logged out."
        }, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        learner_data = None
        if hasattr(user, 'learner_profile'):
            learner_data = LearnerProfileSerializer(user.learner_profile).data

        return Response({
            "user": UserSummarySerializer(user).data,
            "learner_profile": learner_data
        })


class PendingRegistrationsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        pending_learners = Learner.objects.filter(
            user__status=AccountStatus.PENDING
        ).select_related('user').order_by('created_at')

        serializer = LearnerProfileSerializer(pending_learners, many=True)
        return Response(serializer.data)


class ApproveRegistrationView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, learner_id):
        reason = request.data.get('reason', '')
        approval = AuthService.approve_registration(
            learner_id=learner_id,
            admin_user=request.user,
            reason=reason,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response({
            "success": True,
            "message": f"Learner {learner_id} registration APPROVED.",
            "approval": RegistrationApprovalSerializer(approval).data
        })


class RejectRegistrationView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, learner_id):
        reason = request.data.get('reason', '')
        approval = AuthService.reject_registration(
            learner_id=learner_id,
            admin_user=request.user,
            reason=reason,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response({
            "success": True,
            "message": f"Learner {learner_id} registration REJECTED.",
            "approval": RegistrationApprovalSerializer(approval).data
        })


# -------------------------------------------------------------------------
# COURSES & PREREQUISITES
# -------------------------------------------------------------------------

class CourseListCreateView(APIView):
    permission_classes = [IsActiveApprovedUser]

    def get(self, request):
        courses = Course.objects.filter(is_active=True).prefetch_related('content_items')
        learner = getattr(request.user, 'learner_profile', None)

        results = []
        for c in courses:
            data = CourseSerializer(c).data
            # If the requesting user is a learner, compute real-time prerequisite eligibility
            if learner:
                eligibility = PrerequisiteService.evaluate_course_eligibility(learner, c)
                data['eligibility'] = eligibility
                # Check if enrolled
                enrollment = CourseEnrollment.objects.filter(learner=learner, course=c).first()
                data['is_enrolled'] = enrollment is not None
                data['enrollment_progress'] = enrollment.progress_percentage if enrollment else 0.0
                data['enrollment_status'] = enrollment.status if enrollment else None

            results.append(data)

        return Response(results)

    def post(self, request):
        # Only Instructors and Platform Admins can create courses
        if not (request.user.is_instructor() or request.user.is_platform_admin()):
            raise PermissionDenied("Only instructors or platform administrators can create courses.")

        serializer = CourseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save(created_by=request.user)
        return Response(CourseSerializer(course).data, status=status.HTTP_201_CREATED)


class CourseDetailView(APIView):
    permission_classes = [IsActiveApprovedUser]

    def get(self, request, course_id):
        course = get_object_or_404(Course, course_id=course_id)
        data = CourseSerializer(course).data

        # Add contents
        contents = course.content_items.filter(is_active=True).order_by('order')
        data['contents'] = ContentItemSerializer(contents, many=True).data

        # Add assessments
        assessments = course.assessments.all()
        data['assessments'] = AssessmentSerializer(assessments, many=True).data

        learner = getattr(request.user, 'learner_profile', None)
        if learner:
            data['eligibility'] = PrerequisiteService.evaluate_course_eligibility(learner, course)

        return Response(data)


class CourseEnrollView(APIView):
    permission_classes = [IsLearner]

    def post(self, request, course_id):
        course = get_object_or_404(Course, course_id=course_id)
        learner = request.user.learner_profile

        # CRITICAL BACKEND ENFORCEMENT OF PREREQUISITES
        eligibility = PrerequisiteService.evaluate_course_eligibility(learner, course)
        if not eligibility['is_eligible']:
            return Response({
                "success": False,
                "error_type": "PrerequisiteGatingError",
                "message": f"Cannot enroll in advanced course '{course.title}'. Prerequisite requirements not satisfied.",
                "eligibility_details": eligibility
            }, status=status.HTTP_403_FORBIDDEN)

        enrollment, created = CourseEnrollment.objects.get_or_create(
            learner=learner,
            course=course,
            defaults={
                'status': EnrollmentStatus.ENROLLED,
                'progress_percentage': 0.0
            }
        )

        # Trigger automatic learning path creation
        LearningPathService.generate_path_for_course(learner, course, actor=request.user)

        return Response({
            "success": True,
            "message": f"Successfully enrolled in {course.title}.",
            "enrollment_id": enrollment.id,
            "status": enrollment.status
        }, status=status.HTTP_200_OK)


# -------------------------------------------------------------------------
# SKILLS & CONTENT
# -------------------------------------------------------------------------

class SkillListCreateView(APIView):
    permission_classes = [IsActiveApprovedUser]

    def get(self, request):
        skills = Skill.objects.all().order_by('category', 'name')
        return Response(SkillSerializer(skills, many=True).data)

    def post(self, request):
        if not (request.user.is_instructor() or request.user.is_platform_admin()):
            raise PermissionDenied("Only instructors or platform administrators can create skills.")

        serializer = SkillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        skill = serializer.save()
        return Response(SkillSerializer(skill).data, status=status.HTTP_201_CREATED)


class SkillPrerequisiteCreateView(APIView):
    permission_classes = [IsInstructor]

    def post(self, request):
        parent_id = request.data.get('parent_skill')
        prereq_id = request.data.get('prerequisite_skill')
        required_mastery = float(request.data.get('required_mastery_level', 70.0))

        parent = get_object_or_404(Skill, skill_id=parent_id)
        prereq = get_object_or_404(Skill, skill_id=prereq_id)

        if parent == prereq:
            raise ValidationError("A skill cannot have itself as a prerequisite.")

        edge, _ = SkillPrerequisite.objects.get_or_create(
            parent_skill=parent,
            prerequisite_skill=prereq,
            defaults={'required_mastery_level': required_mastery}
        )

        # Check for circular dependency
        cycles = PrerequisiteService.detect_skill_cycles()
        if cycles:
            edge.delete()
            raise ValidationError(f"Cannot add prerequisite: creates a cyclic loop: {cycles}")

        return Response({
            "success": True,
            "message": f"Prerequisite configured: {parent.code} requires {prereq.code} (>= {required_mastery}%)."
        }, status=status.HTTP_201_CREATED)


class ContentListCreateView(APIView):
    permission_classes = [IsActiveApprovedUser]

    def get(self, request):
        course_id = request.query_params.get('course')
        query = ContentItem.objects.filter(is_active=True)
        if course_id:
            query = query.filter(course__course_id=course_id)
        return Response(ContentItemSerializer(query, many=True).data)

    def post(self, request):
        if not (request.user.is_instructor() or request.user.is_platform_admin()):
            raise PermissionDenied("Only instructors or platform administrators can create learning content.")

        serializer = ContentItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        return Response(ContentItemSerializer(item).data, status=status.HTTP_201_CREATED)


class ContentSkillMapView(APIView):
    permission_classes = [IsInstructor]

    def post(self, request, content_id):
        item = get_object_or_404(ContentItem, content_id=content_id)
        skill_id = request.data.get('skill')
        weight = float(request.data.get('relevance_weight', 1.0))

        skill = get_object_or_404(Skill, skill_id=skill_id)
        mapping, _ = ContentSkill.objects.update_or_create(
            content_item=item,
            skill=skill,
            defaults={'relevance_weight': weight}
        )
        return Response({
            "success": True,
            "message": f"Mapped content '{item.title}' to skill '{skill.name}' with weight {weight}."
        })


# -------------------------------------------------------------------------
# ASSESSMENTS & ATTEMPTS
# -------------------------------------------------------------------------

class AssessmentListView(APIView):
    permission_classes = [IsActiveApprovedUser]

    def get(self, request):
        course_id = request.query_params.get('course')
        query = Assessment.objects.select_related('course', 'skill').all()
        if course_id:
            query = query.filter(course__course_id=course_id)
        return Response(AssessmentSerializer(query, many=True).data)


class AssessmentStartView(APIView):
    permission_classes = [IsLearner]

    def post(self, request, assessment_id):
        learner = request.user.learner_profile
        content_item_id = request.data.get('content_item_id')

        attempt = AssessmentService.start_assessment_attempt(
            learner=learner,
            assessment_id=assessment_id,
            content_item_id=content_item_id
        )

        assessment = attempt.assessment
        questions = AssessmentQuestion.objects.filter(assessment=assessment).order_by('order')

        return Response({
            "success": True,
            "attempt_id": attempt.attempt_id,
            "assessment_id": assessment.assessment_id,
            "title": assessment.title,
            "time_limit_minutes": assessment.time_limit_minutes,
            "questions": [
                {
                    "id": q.id,
                    "order": q.order,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "options": q.options_json,
                    "points": q.points
                }
                for q in questions
            ]
        })


class AssessmentSubmitView(APIView):
    permission_classes = [IsLearner]

    def post(self, request, assessment_id):
        attempt_id = request.data.get('attempt_id')
        responses = request.data.get('responses', [])

        result = AssessmentService.submit_assessment_attempt(
            attempt_id=attempt_id,
            responses=responses,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response(result)


class AssessmentResultsView(APIView):
    permission_classes = [IsActiveApprovedUser]

    def get(self, request):
        user = request.user
        if user.is_learner():
            attempts = Attempt.objects.filter(learner=user.learner_profile).select_related('assessment').order_by('-completed_at')
        else:
            attempts = Attempt.objects.select_related('learner', 'assessment').order_by('-completed_at')[:100]

        return Response(AttemptSerializer(attempts, many=True).data)


# -------------------------------------------------------------------------
# MASTERY & RECOMMENDATIONS
# -------------------------------------------------------------------------

class LearnerMasteryView(APIView):
    permission_classes = [IsLearner]

    def get(self, request):
        learner = request.user.learner_profile
        summary = MasteryService.get_learner_mastery_summary(learner)
        return Response(summary)


class GenerateRecommendationsView(APIView):
    permission_classes = [IsLearner]

    def post(self, request):
        learner = request.user.learner_profile
        recs = RecommendationService.generate_recommendations(
            learner=learner,
            max_recommendations=5,
            actor=request.user,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response(recs)


class LearnerRecommendationsView(APIView):
    permission_classes = [IsLearner]

    def get(self, request):
        learner = request.user.learner_profile
        recs = RecommendationService.get_active_recommendations(learner)
        return Response(recs)


# -------------------------------------------------------------------------
# LEARNING PATHS
# -------------------------------------------------------------------------

class LearnerPathView(APIView):
    permission_classes = [IsLearner]

    def get(self, request):
        learner = request.user.learner_profile
        path_data = LearningPathService.get_learner_path_details(learner)
        return Response(path_data or {"message": "No active learning path found. Enroll in a course to initiate your trajectory."})


class GeneratePathView(APIView):
    permission_classes = [IsLearner]

    def post(self, request):
        learner = request.user.learner_profile
        course_id = request.data.get('course_id')
        course = get_object_or_404(Course, course_id=course_id)

        path = LearningPathService.generate_path_for_course(learner, course, actor=request.user)
        path_details = LearningPathService.get_learner_path_details(learner)
        return Response(path_details, status=status.HTTP_201_CREATED)


# -------------------------------------------------------------------------
# ANALYTICS & DATA VALIDATION
# -------------------------------------------------------------------------

class AdminAnalyticsView(APIView):
    permission_classes = [IsAcademicAdmin]

    def get(self, request):
        total_learners = Learner.objects.count()
        active_learners = Learner.objects.filter(user__status=AccountStatus.ACTIVE).count()
        total_enrollments = CourseEnrollment.objects.count()
        completed_enrollments = CourseEnrollment.objects.filter(status=EnrollmentStatus.COMPLETED).count()
        completion_rate = round((completed_enrollments / total_enrollments * 100.0) if total_enrollments > 0 else 0.0, 1)

        # Average mastery across all masteries
        masteries = SkillMastery.objects.all()
        avg_mastery = round(sum(m.mastery_percentage for m in masteries) / masteries.count(), 1) if masteries.exists() else 0.0

        # Skill Gaps: Skills with highest count of NEEDS_IMPROVEMENT
        weakest_skills = SkillMastery.objects.filter(
            mastery_percentage__lt=70.0
        ).values('skill__name', 'skill__code').annotate(c=Count('id')).order_by('-c')[:5]

        return Response({
            "total_learners": total_learners,
            "active_learners": active_learners,
            "total_enrollments": total_enrollments,
            "completed_enrollments": completed_enrollments,
            "completion_rate_percentage": completion_rate,
            "average_mastery_percentage": avg_mastery,
            "skill_gaps": list(weakest_skills)
        })


class DataValidationBenchmarkView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        metrics = ValidationService.run_full_validation_suite()
        return Response(metrics)


# -------------------------------------------------------------------------
# SUPPORT TICKETS
# -------------------------------------------------------------------------

class SupportTicketListView(APIView):
    permission_classes = [IsActiveApprovedUser]

    def get(self, request):
        user = request.user
        if user.is_learner():
            tickets = SupportTicket.objects.filter(learner=user.learner_profile).order_by('-created_at')
        else:
            tickets = SupportTicket.objects.all().order_by('-created_at')
        return Response(SupportTicketSerializer(tickets, many=True).data)

    def post(self, request):
        if not request.user.is_learner():
            raise PermissionDenied("Only learners can submit support tickets.")

        learner = request.user.learner_profile
        ticket_id = f"TCK-{SupportTicket.objects.count() + 1:06d}"
        ticket = SupportTicket.objects.create(
            ticket_id=ticket_id,
            learner=learner,
            category=request.data.get('category', 'OTHER'),
            subject=request.data.get('subject', 'Assistance Request'),
            description=request.data.get('description', '')
        )
        return Response(SupportTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)


class SupportTicketUpdateView(APIView):
    permission_classes = [IsSupportStaff]

    def post(self, request, ticket_id):
        ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
        status_choice = request.data.get('status')
        resolution = request.data.get('resolution')

        if status_choice:
            ticket.status = status_choice
        if resolution:
            ticket.resolution = resolution
        ticket.assigned_to = request.user
        ticket.save()

        return Response(SupportTicketSerializer(ticket).data)
