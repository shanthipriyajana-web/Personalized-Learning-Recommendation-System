"""
Automated Test Suite: Authentication, Open Registration & RBAC.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from learning_system.models import User, UserRole, AccountStatus, Learner
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

    def test_registration_creates_active_account(self):
        """
        Registration creates an ACTIVE account immediately (no admin approval).
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
        self.assertEqual(learner.user.status, AccountStatus.ACTIVE)
        self.assertTrue(learner.user.is_active_approved())

    def test_new_user_can_login_immediately(self):
        """
        A newly registered user can sign in without any approval step.
        """
        AuthService.register_learner(
            username='new_user',
            email='new@test.edu',
            password='Password123!'
        )

        login_res = self.client.post('/api/auth/login', {
            'username': 'new_user',
            'password': 'Password123!'
        }, format='json')

        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertTrue(login_res.data['success'])

    def test_suspended_user_cannot_login(self):
        """
        Suspended accounts are still blocked from signing in.
        """
        learner = AuthService.register_learner(
            username='suspended_user',
            email='susp@test.edu',
            password='Password123!'
        )
        learner.user.status = AccountStatus.SUSPENDED
        learner.user.save()

        login_res = self.client.post('/api/auth/login', {
            'username': 'suspended_user',
            'password': 'Password123!'
        }, format='json')

        self.assertEqual(login_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('suspended', login_res.data['message'].lower())

    def test_rbac_learner_cannot_access_admin_endpoints(self):
        """
        Learner cannot access admin endpoints (RBAC 403 Forbidden).
        """
        learner = AuthService.register_learner(
            username='regular_learner',
            email='regular@test.edu',
            password='Password123!'
        )

        self.client.force_authenticate(user=learner.user)
        response = self.client.get('/api/admin/analytics')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
