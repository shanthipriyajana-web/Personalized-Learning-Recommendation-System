"""
Authentication & Authorization Service.
Enforces Role-Based Access Control (RBAC) and Mandatory Learner Registration Approval.
"""

from django.contrib.auth import authenticate
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from learning_system.models import (
    User, UserRole, AccountStatus, Learner, RegistrationApproval,
    ApprovalDecision
)
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

    @staticmethod
    def generate_next_approval_id() -> str:
        """
        Generates sequentially ordered approval ID: APR-000001
        """
        count = RegistrationApproval.objects.count() + 1
        while True:
            candidate_id = f"APR-{count:06d}"
            if not RegistrationApproval.objects.filter(approval_id=candidate_id).exists():
                return candidate_id
            count += 1

    @classmethod
    @transaction.atomic
    def register_learner(cls, username: str, email: str, password: str,
                         first_name: str = '', last_name: str = '',
                         education_level: str = 'UNDERGRADUATE',
                         learning_goals: str = '', phone_number: str = '',
                         ip_address: str = None) -> Learner:
        """
        Public registration workflow:
        Creates user account with status=PENDING.
        The user CANNOT log in until an authorized Platform Administrator approves.
        """
        if User.objects.filter(username=username).exists():
            raise ValidationError(f"Username '{username}' is already taken.")
        if email and User.objects.filter(email=email).exists():
            raise ValidationError(f"Email '{email}' is already registered.")

        # Create user with role LEARNER and status PENDING
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.LEARNER,
            status=AccountStatus.PENDING,
            phone_number=phone_number
        )

        learner_id = cls.generate_next_learner_id()
        learner = Learner.objects.create(
            learner_id=learner_id,
            user=user,
            current_education_level=education_level,
            learning_goals=learning_goals
        )

        AuditService.log_event(
            action="LEARNER_REGISTERED",
            entity_type="Learner",
            entity_id=learner.learner_id,
            actor=user,
            details={
                "username": username,
                "email": email,
                "status": AccountStatus.PENDING,
            },
            ip_address=ip_address
        )

        return learner

    @classmethod
    @transaction.atomic
    def approve_registration(cls, learner_id: str, admin_user: User, reason: str = '', ip_address: str = None) -> RegistrationApproval:
        """
        Platform Administrator approves a pending learner registration.
        Transitions account status from PENDING to ACTIVE.
        """
        if not admin_user.is_platform_admin():
            raise PermissionDenied("Only authorized Platform Administrators can approve registrations.")

        try:
            learner = Learner.objects.select_related('user').get(learner_id=learner_id)
        except Learner.DoesNotExist:
            raise ValidationError(f"Learner with ID '{learner_id}' not found.")

        user = learner.user
        if user.status != AccountStatus.PENDING:
            raise ValidationError(f"Cannot approve user with current status '{user.status}'. Must be PENDING.")

        user.status = AccountStatus.ACTIVE
        user.is_active = True
        user.save(update_fields=['status', 'is_active', 'updated_at'])

        approval = RegistrationApproval.objects.create(
            approval_id=cls.generate_next_approval_id(),
            learner=learner,
            reviewed_by=admin_user,
            decision=ApprovalDecision.APPROVED,
            reason=reason or "Registration verified and approved by Platform Administrator."
        )

        AuditService.log_event(
            action="REGISTRATION_APPROVED",
            entity_type="Learner",
            entity_id=learner.learner_id,
            actor=admin_user,
            details={
                "approval_id": approval.approval_id,
                "decision": ApprovalDecision.APPROVED,
                "reason": approval.reason
            },
            ip_address=ip_address
        )

        return approval

    @classmethod
    @transaction.atomic
    def reject_registration(cls, learner_id: str, admin_user: User, reason: str = '', ip_address: str = None) -> RegistrationApproval:
        """
        Platform Administrator rejects a pending learner registration.
        Transitions account status to REJECTED.
        """
        if not admin_user.is_platform_admin():
            raise PermissionDenied("Only authorized Platform Administrators can reject registrations.")

        try:
            learner = Learner.objects.select_related('user').get(learner_id=learner_id)
        except Learner.DoesNotExist:
            raise ValidationError(f"Learner with ID '{learner_id}' not found.")

        user = learner.user
        user.status = AccountStatus.REJECTED
        user.is_active = False
        user.save(update_fields=['status', 'is_active', 'updated_at'])

        approval = RegistrationApproval.objects.create(
            approval_id=cls.generate_next_approval_id(),
            learner=learner,
            reviewed_by=admin_user,
            decision=ApprovalDecision.REJECTED,
            reason=reason or "Registration does not meet platform admission criteria."
        )

        AuditService.log_event(
            action="REGISTRATION_REJECTED",
            entity_type="Learner",
            entity_id=learner.learner_id,
            actor=admin_user,
            details={
                "approval_id": approval.approval_id,
                "decision": ApprovalDecision.REJECTED,
                "reason": approval.reason
            },
            ip_address=ip_address
        )

        return approval

    @staticmethod
    def authenticate_with_status_check(username: str, password: str):
        """
        Authenticates user credentials and checks lifecycle status.
        Raises descriptive errors if status is PENDING, REJECTED, or SUSPENDED.
        """
        user = authenticate(username=username, password=password)
        if user is None:
            # Check if user exists to provide helpful status guidance
            existing_user = User.objects.filter(username=username).first()
            if existing_user:
                if existing_user.status == AccountStatus.PENDING:
                    raise ValidationError(
                        "Your registration is pending approval by a Platform Administrator. "
                        "You will receive access once approved."
                    )
                elif existing_user.status == AccountStatus.REJECTED:
                    raise ValidationError(
                        "Your registration was rejected by the administrator. Access denied."
                    )
                elif existing_user.status == AccountStatus.SUSPENDED:
                    raise ValidationError(
                        "Your account has been suspended. Please contact platform support."
                    )
            raise ValidationError("Invalid username or password.")

        if user.status == AccountStatus.PENDING:
            raise ValidationError(
                "Your registration is pending approval by a Platform Administrator. "
                "You will receive access once approved."
            )
        elif user.status == AccountStatus.REJECTED:
            raise ValidationError("Your account was rejected by an administrator. Access denied.")
        elif user.status == AccountStatus.SUSPENDED:
            raise ValidationError("Your account has been suspended. Please contact support.")

        return user
