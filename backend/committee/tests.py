from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models import CustomUser, Role, Office
from .models import Committee, CommitteeMembership
from procurement.models import ProcurementPlan
from django.urls import reverse
import json


class CommitteeAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create a superadmin role
        self.superadmin_role, _ = Role.objects.get_or_create(name='Super Admin')

        # Create a regular role
        self.md_role, _ = Role.objects.get_or_create(name='Regular User')
        
        # Create an office
        self.office, _ = Office.objects.get_or_create(name='NTC', code='NTC')

        # Create users with provided credentials
        self.superadmin = CustomUser.objects.create_superuser(
            employee_id='admin',
            email='superadmin@gmail.com',
            password='Nepal@123',
            user_role=self.superadmin_role,
            office=self.office
        )
        self.user = CustomUser.objects.create_user(
            employee_id='7778',
            email='susmitasharmapaudel@gmail.com',
            password='Nepal@123',
            user_role=self.md_role,
            office=self.office
        )

        # Create a procurement plan for testing
        self.procurement_plan = ProcurementPlan.objects.create(
            project_name='Test Project',
            project_description='Test Description',
            estimated_cost=100000,
            owner=self.superadmin,
            office=self.office
        )

        # Authenticate as superadmin for setup
        self.client.force_authenticate(user=self.superadmin)

    def test_create_committee(self):
        url = '/api/committee/committees/create/'
        data = {
            'name': 'New Committee',
            'purpose': 'Test committee purpose',
            'committee_type': 'other',
            'formation_date': '2025-04-01',
            'deadline': '2025-05-01',
            'should_notify': True,
            'members': [
                {'employeeId': '7778', 'role': 'member'}
            ],
            'approval_status': 'active'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Committee.objects.count(), 1)
        self.assertEqual(Committee.objects.first().created_by, self.superadmin)

    def test_committee_permission(self):
        # Create a committee as superadmin
        committee = Committee.objects.create(
            name='Restricted Committee',
            formation_date='2025-04-01',
            purpose='Restricted purpose',
            committee_type='other',
            created_by=self.superadmin
        )

        # Verify the committee exists
        self.assertTrue(Committee.objects.filter(id=committee.id).exists())

        # Switch to regular user
        self.client.force_authenticate(user=self.user)
        url = f'/api/committee/committees/{committee.id}/'

        # Regular user should not have access unless member or creator
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Add user as member
        CommitteeMembership.objects.create(
            user=self.user,
            committee=committee,
            committee_role='member'
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def tearDown(self):
        self.client.force_authenticate(user=None)
