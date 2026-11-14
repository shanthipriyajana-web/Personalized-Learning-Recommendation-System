"""
URL Configuration for Personalized Learning Recommendation System.
"""

from django.contrib import admin
from django.urls import path, include
from learning_system.views import (
    index_view, login_page, register_page, pending_approval_page,
    learner_dashboard, instructor_dashboard, academic_dashboard,
    support_dashboard, platform_admin_dashboard
)

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Web Views (Presentation Tier)
    path('', index_view, name='index'),
    path('login/', login_page, name='login_page'),
    path('register/', register_page, name='register_page'),
    path('pending-approval/', pending_approval_page, name='pending_approval'),

    # Dashboards (Role-Based Access)
    path('dashboard/learner/', learner_dashboard, name='learner_dashboard'),
    path('dashboard/instructor/', instructor_dashboard, name='instructor_dashboard'),
    path('dashboard/academic/', academic_dashboard, name='academic_dashboard'),
    path('dashboard/support/', support_dashboard, name='support_dashboard'),
    path('dashboard/admin/', platform_admin_dashboard, name='platform_admin_dashboard'),

    # Application Layer REST API
    path('api/', include('learning_system.api.urls')),
]
