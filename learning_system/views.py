"""
Presentation Layer Views for Web Interface.
Renders responsive templates for Public auth and the 5 Role-based Dashboards.
Client-side interactivity and data retrieval communicate strictly via RESTful APIs.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from learning_system.models import UserRole, AccountStatus


def index_view(request):
    """
    Landing router. If logged in, routes to the appropriate role dashboard.
    If not, renders login page.
    """
    if request.user.is_authenticated:
        if request.user.status == AccountStatus.PENDING:
            return redirect('pending_approval')
        elif request.user.status in [AccountStatus.REJECTED, AccountStatus.SUSPENDED]:
            return redirect('login_page')

        role = request.user.role
        if role == UserRole.LEARNER:
            return redirect('learner_dashboard')
        elif role == UserRole.INSTRUCTOR:
            return redirect('instructor_dashboard')
        elif role == UserRole.ACADEMIC_ADMIN:
            return redirect('academic_dashboard')
        elif role == UserRole.SUPPORT_STAFF:
            return redirect('support_dashboard')
        elif role == UserRole.PLATFORM_ADMIN or request.user.is_superuser:
            return redirect('platform_admin_dashboard')

    return redirect('login_page')


def login_page(request):
    if request.user.is_authenticated and request.user.status == AccountStatus.ACTIVE:
        return redirect('index')
    return render(request, 'auth/login.html')


def register_page(request):
    return render(request, 'auth/register.html')


def pending_approval_page(request):
    return render(request, 'auth/pending_approval.html')


@login_required(login_url='login_page')
def learner_dashboard(request):
    if request.user.status != AccountStatus.ACTIVE or request.user.role != UserRole.LEARNER:
        return redirect('index')
    return render(request, 'dashboards/learner_dashboard.html', {
        'learner': getattr(request.user, 'learner_profile', None)
    })


@login_required(login_url='login_page')
def instructor_dashboard(request):
    if request.user.status != AccountStatus.ACTIVE or not (request.user.role == UserRole.INSTRUCTOR or request.user.is_platform_admin()):
        return redirect('index')
    return render(request, 'dashboards/instructor_dashboard.html')


@login_required(login_url='login_page')
def academic_dashboard(request):
    if request.user.status != AccountStatus.ACTIVE or not (request.user.role == UserRole.ACADEMIC_ADMIN or request.user.is_platform_admin()):
        return redirect('index')
    return render(request, 'dashboards/academic_dashboard.html')


@login_required(login_url='login_page')
def support_dashboard(request):
    if request.user.status != AccountStatus.ACTIVE or not (request.user.role == UserRole.SUPPORT_STAFF or request.user.is_platform_admin()):
        return redirect('index')
    return render(request, 'dashboards/support_dashboard.html')


@login_required(login_url='login_page')
def platform_admin_dashboard(request):
    if request.user.status != AccountStatus.ACTIVE or not request.user.is_platform_admin():
        return redirect('index')
    return render(request, 'dashboards/platform_admin_dashboard.html')
