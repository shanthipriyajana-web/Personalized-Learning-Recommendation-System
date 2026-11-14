"""
RESTful API URL Routing Configuration.
"""

from django.urls import path
from learning_system.api.views import (
    RegisterView, LoginView, LogoutView, MeView,
    CourseListCreateView, CourseDetailView, CourseEnrollView,
    SkillListCreateView, SkillPrerequisiteCreateView,
    ContentListCreateView, ContentSkillMapView,
    AssessmentListView, AssessmentStartView, AssessmentSubmitView, AssessmentResultsView,
    LearnerMasteryView, GenerateRecommendationsView, LearnerRecommendationsView,
    LearnerPathView, GeneratePathView,
    AdminAnalyticsView, DataValidationBenchmarkView,
    SupportTicketListView, SupportTicketUpdateView
)

urlpatterns = [
    # Authentication
    path('auth/register', RegisterView.as_view(), name='api-register'),
    path('auth/login', LoginView.as_view(), name='api-login'),
    path('auth/logout', LogoutView.as_view(), name='api-logout'),
    path('auth/me', MeView.as_view(), name='api-me'),

    # Courses & Prerequisite Gating
    path('courses', CourseListCreateView.as_view(), name='api-courses'),
    path('courses/<str:course_id>', CourseDetailView.as_view(), name='api-course-detail'),
    path('courses/<str:course_id>/enroll', CourseEnrollView.as_view(), name='api-course-enroll'),

    # Skills
    path('skills', SkillListCreateView.as_view(), name='api-skills'),
    path('skills/prerequisites', SkillPrerequisiteCreateView.as_view(), name='api-skill-prerequisites'),

    # Educational Content
    path('content', ContentListCreateView.as_view(), name='api-content'),
    path('content/<str:content_id>/map-skills', ContentSkillMapView.as_view(), name='api-content-map-skills'),

    # Assessments & Attempts
    path('assessments', AssessmentListView.as_view(), name='api-assessments'),
    path('assessments/<str:assessment_id>/start', AssessmentStartView.as_view(), name='api-assessment-start'),
    path('assessments/<str:assessment_id>/submit', AssessmentSubmitView.as_view(), name='api-assessment-submit'),
    path('assessments/results', AssessmentResultsView.as_view(), name='api-assessment-results'),

    # Mastery
    path('learners/me/mastery', LearnerMasteryView.as_view(), name='api-learner-mastery'),

    # Recommendations
    path('recommendations/generate', GenerateRecommendationsView.as_view(), name='api-recommendations-generate'),
    path('recommendations/me', LearnerRecommendationsView.as_view(), name='api-recommendations-me'),

    # Learning Paths
    path('learning-paths/me', LearnerPathView.as_view(), name='api-learning-paths-me'),
    path('learning-paths', GeneratePathView.as_view(), name='api-learning-paths-create'),

    # Administrative Analytics & Benchmarks
    path('admin/analytics', AdminAnalyticsView.as_view(), name='api-admin-analytics'),
    path('admin/data-validation', DataValidationBenchmarkView.as_view(), name='api-admin-data-validation'),

    # Support Tickets
    path('support/tickets', SupportTicketListView.as_view(), name='api-support-tickets'),
    path('support/tickets/<str:ticket_id>/update', SupportTicketUpdateView.as_view(), name='api-support-ticket-update'),
]
