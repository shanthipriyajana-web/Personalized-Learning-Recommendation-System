"""
Authentication & Authorization Service.
Enforces Role-Based Access Control (RBAC) and account lifecycle checks.
"""

from django.contrib.auth import authenticate
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from learning_system.models import User, UserRole, AccountStatus, Learner
from learning_system.services.audit_service import AuditService


class AuthService:
    @staticmethod
    def generate_next_learner_id() -> str:
        """
        Generates sequentially ordered immutable ID: LRN-000001
        """
        count = Learner.objects.count() + 1
        # In case records were deleted or custom IDs exist, ensure uniqueness
        while True:
            candidate_id = f"LRN-{count:06d}"
            if not Learner.objects.filter(learner_id=candidate_id).exists():
                return candidate_id
            count += 1

    @classmethod
    @transaction.atomic
    def register_user(cls, username: str, email: str, password: str,
                      role: str = UserRole.STUDENT,
                      first_name: str = '', last_name: str = '',
                      education_level: str = 'UNDERGRADUATE',
                      learning_goals: str = '', phone_number: str = '',
                      ip_address: str = None) -> User:
        """
        Public registration workflow for all non-admin roles:
        Supports STUDENT, INSTRUCTOR, ACADEMIC_ADMIN, and SUPPORT_STAFF.
        Accounts are ACTIVE immediately - no administrator approval is required.
        Only ONE Platform Administrator is permitted on the platform.
        """
        # Strict enforcement: Platform Administrator cannot be registered publicly
        if role == UserRole.PLATFORM_ADMIN:
            raise ValidationError("Platform Administrator accounts cannot be registered publicly. Only one Platform Administrator is permitted.")

        # Ensure no duplicate Platform Administrator can ever be registered
        if role == UserRole.PLATFORM_ADMIN and User.objects.filter(role=UserRole.PLATFORM_ADMIN).exists():
            raise ValidationError("Platform Administrator already exists. Only one Platform Administrator is allowed on the system.")

        valid_registration_roles = [
            UserRole.STUDENT,
            UserRole.INSTRUCTOR,
            UserRole.ACADEMIC_ADMIN,
            UserRole.SUPPORT_STAFF,
            'LEARNER'  # backward compatibility
        ]
        if role not in valid_registration_roles:
            raise ValidationError(f"Invalid registration role '{role}'. Permitted roles: Student, Instructor, Academic Administrator, Support Staff.")

        # Standardize role name
        assigned_role = UserRole.STUDENT if role in [UserRole.STUDENT, 'LEARNER'] else role

        if User.objects.filter(username=username).exists():
            raise ValidationError(f"Username '{username}' is already taken.")
        if email and User.objects.filter(email=email).exists():
            raise ValidationError(f"Email '{email}' is already registered.")

        # Create user with chosen role; account is usable immediately
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=assigned_role,
            status=AccountStatus.ACTIVE,
            phone_number=phone_number
        )

        learner = None
        if assigned_role == UserRole.STUDENT:
            learner_id = cls.generate_next_learner_id()
            learner = Learner.objects.create(
                learner_id=learner_id,
                user=user,
                current_education_level=education_level,
                learning_goals=learning_goals
            )

        AuditService.log_event(
            action="USER_REGISTERED",
            entity_type="User",
            entity_id=user.username,
            actor=user,
            details={
                "username": username,
                "email": email,
                "role": assigned_role,
                "status": AccountStatus.ACTIVE,
                "learner_id": learner.learner_id if learner else None
            },
            ip_address=ip_address
        )

        return user

    @classmethod
    def register_learner(cls, username: str, email: str, password: str,
                         first_name: str = '', last_name: str = '',
                         education_level: str = 'UNDERGRADUATE',
                         learning_goals: str = '', phone_number: str = '',
                         ip_address: str = None) -> Learner:
        """
        Backward-compatible helper registering a student/learner.
        """
        user = cls.register_user(
            username=username,
            email=email,
            password=password,
            role=UserRole.STUDENT,
            first_name=first_name,
            last_name=last_name,
            education_level=education_level,
            learning_goals=learning_goals,
            phone_number=phone_number,
            ip_address=ip_address
        )
        return user.learner_profile

    @staticmethod
    def authenticate_with_status_check(username: str, password: str):
        """
        Authenticates user credentials and checks the account is not suspended.
        """
        user = authenticate(username=username, password=password)
        if user is None:
            existing_user = User.objects.filter(username=username).first()
            if existing_user and existing_user.status == AccountStatus.SUSPENDED:
                raise ValidationError("Your account has been suspended. Please contact platform support.")
            raise ValidationError("Invalid username or password.")

        if user.status == AccountStatus.SUSPENDED:
            raise ValidationError("Your account has been suspended. Please contact support.")

        return user
