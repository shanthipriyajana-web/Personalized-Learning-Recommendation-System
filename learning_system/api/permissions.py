"""
Role-Based Access Control (RBAC) Custom Permissions for REST API.
Enforces role separation and active-account checks.
"""

from rest_framework import permissions
from learning_system.models import UserRole, AccountStatus


class IsActiveApprovedUser(permissions.BasePermission):
    """
    Ensures user account is authenticated and active.
    """
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and
            user.is_authenticated and
            user.is_active and
            user.status == AccountStatus.ACTIVE
        )


class IsLearner(permissions.BasePermission):
    """
    Allows access only to authenticated, active Students / Learners.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_student() and
            request.user.status == AccountStatus.ACTIVE
        )


IsStudent = IsLearner


class IsInstructor(permissions.BasePermission):
    """
    Allows access only to Instructors or Platform Admins.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == UserRole.INSTRUCTOR or request.user.is_platform_admin()) and
            request.user.status == AccountStatus.ACTIVE
        )


class IsAcademicAdmin(permissions.BasePermission):
    """
    Allows access only to Academic Administrators or Platform Admins.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == UserRole.ACADEMIC_ADMIN or request.user.is_platform_admin()) and
            request.user.status == AccountStatus.ACTIVE
        )


class IsSupportStaff(permissions.BasePermission):
    """
    Allows access only to Support Staff or Platform Admins.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == UserRole.SUPPORT_STAFF or request.user.is_platform_admin()) and
            request.user.status == AccountStatus.ACTIVE
        )


class IsPlatformAdmin(permissions.BasePermission):
    """
    Strict permission: Platform Administrators only.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_platform_admin() and
            request.user.status == AccountStatus.ACTIVE
        )
