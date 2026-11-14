"""
Automated Test Suite: Authentication, Mandatory Registration Approval & RBAC.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from learning_system.models import User, UserRole, AccountStatus, Learner, RegistrationApproval
from learning_system.services.auth_service import AuthService

User = get_user_model()


class AuthAndRBACркаTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create Platform Admin
        self.admin_user = User.objects.create_superuser(
            username='sys_admin',
            email='admin@test.edu',
            password='Password123!',
            role=UserRole.PLATFORM_ADMIN,
            status=AccountStatus.ACTIVE
        )

        # Create Instructor
        self.instructor_user = User.objects.create_user(
            username='instructor_bob',
            email='bob@test.edu',
            password='Password123!',
            role=UserRole.INSTRUCTOR,
            status=AccountStatus.ACTIVE
        )

    def test_learner_registration_creates_pending_account(self):
        """
        Learner registration must create an account with status PENDING.
        """
        payload = {
            'username': 'john_doe',
            'email': 'john@test.edu',
            'password': 'SecurePassword123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'education_level': 'UNDERGRADUATE',
            'learning_goals': 'Python mastery'
        }
        response = self.client.post('/api/auth/register', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        learner = Learner.objects.get(user__username='john_doe')
        self.assertTrue(learner.learner_id.startswith('LRN-'))
        self.assertEqual(learner.user.status, AccountStatus.PENDING)
        self.assertFalse(learner.user.is_active_approved())

    def test_pending_learner_cannot_authenticate(self):
        """
        Pending learner cannot log in until approved.
        """
        AuthService.register_learner(
            username='pending_user',
            email='pending@test.edu',
            password='Password123!'
        )

        login_res = self.client.post('/api/auth/login', {
            'username': 'pending_user',
            'password': 'Password123!'
        }, format='json')

        self.assertEqual(login_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pending approval', login_res.data['message'].lower())

    def test_platform_admin_approval_activates_account(self):
        """
        Platform Administrator approves registration, transitioning status to ACTIVE.
        """
        learner = AuthService.register_learner(
            username='alice_smith',
            email='alice@test.edu',
            password='Password123!'
        )

        self.client.force_authenticate(user=self.admin_user)
        approve_res = self.client.post(f'/api/admin/registrations/{learner.learner_id}/approve', {
            'reason': 'Academic credentials verified.'
        }, format='json')

        self.assertEqual(approve_res.status_code, status.HTTP_200_OK)
        learner.refresh_from_db()
        self.assertEqual(learner.user.status, AccountStatus.ACTIVE)
        self.assertTrue(learner.user.is_active)

        # Check approval audit record
        approval = RegistrationApproval.objects.get(learner=learner)
        self.assertEqual(approval.decision, 'APPROVED')
        self.assertEqual(approval.reviewed_by, self.admin_user)

    def test_rbac_learner_cannot_access_admin_endpoints(self):
        """
        Learner cannot access pending registrations queue (RBAC 403 Forbidden).
        """
        learner = AuthService.register_learner(
            username='approved_learner',
            email='approved@test.edu',
            password='Password123!'
        )
        AuthService.approve_registration(learner.learner_id, self.admin_user)

        self.client.force_authenticate(user=learner.user)
        response = self.client.get('/api/admin/registrations/pending')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
