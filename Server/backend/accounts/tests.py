from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Staff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_staff(email='staff@test.com', name='Test Staff', role=Staff.Roles.CLERK,
               pin='123456', is_active=True, **kwargs):
    s = Staff.objects.create_user(
        email=email, staffName=name, role=role, password=pin, **kwargs
    )
    s.is_active = is_active
    s.save(update_fields=['is_active'])
    return s


def auth_client(staff):
    client = APIClient()
    token = RefreshToken.for_user(staff)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


# ---------------------------------------------------------------------------
# 1. Model Tests
# ---------------------------------------------------------------------------

class StaffModelTests(TestCase):

    def test_str_representation(self):
        s = make_staff()
        self.assertEqual(str(s), 'Test Staff (Clerical staff)')

    def test_email_is_username_field(self):
        self.assertEqual(Staff.USERNAME_FIELD, 'email')

    def test_create_user_hashes_password(self):
        s = make_staff(pin='654321')
        self.assertTrue(s.check_password('654321'))
        self.assertNotEqual(s.password, '654321')

    def test_create_superuser_sets_flags(self):
        admin = Staff.objects.create_superuser(
            email='admin@test.com', staffName='Admin', password='adminpass'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, Staff.Roles.ADMIN)

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            Staff.objects.create_user(email='', staffName='X', password='123456')

    def test_create_user_requires_name(self):
        with self.assertRaises(ValueError):
            Staff.objects.create_user(email='x@x.com', staffName='', password='123456')

    def test_default_role_is_clerk(self):
        s = make_staff()
        self.assertEqual(s.role, Staff.Roles.CLERK)

    def test_failed_pin_attempts_defaults_to_zero(self):
        s = make_staff()
        self.assertEqual(s.failedPinAttempts, 0)


# ---------------------------------------------------------------------------
# 2. Login Tests
# ---------------------------------------------------------------------------

class LoginTests(APITestCase):

    def setUp(self):
        self.url = reverse('accounts:staff-login')
        self.staff = make_staff(pin='111111')

    def test_login_success_returns_tokens(self):
        res = self.client.post(self.url, {'email': 'staff@test.com', 'pin': '111111'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)
        self.assertEqual(res.data['email'], 'staff@test.com')

    def test_login_wrong_pin(self):
        res = self.client.post(self.url, {'email': 'staff@test.com', 'pin': '000000'})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unknown_email(self):
        res = self.client.post(self.url, {'email': 'nobody@test.com', 'pin': '111111'})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_account(self):
        self.staff.is_active = False
        self.staff.save(update_fields=['is_active'])
        res = self.client.post(self.url, {'email': 'staff@test.com', 'pin': '111111'})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_increments_failed_attempts(self):
        self.client.post(self.url, {'email': 'staff@test.com', 'pin': '000000'})
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.failedPinAttempts, 1)

    def test_login_lockout_after_five_failures(self):
        for _ in range(5):
            self.client.post(self.url, {'email': 'staff@test.com', 'pin': '000000'})
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_login_resets_failed_attempts_on_success(self):
        self.staff.failedPinAttempts = 3
        self.staff.save(update_fields=['failedPinAttempts'])
        self.client.post(self.url, {'email': 'staff@test.com', 'pin': '111111'})
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.failedPinAttempts, 0)

    def test_login_updates_last_login_at(self):
        self.assertIsNone(self.staff.lastLoginAt)
        self.client.post(self.url, {'email': 'staff@test.com', 'pin': '111111'})
        self.staff.refresh_from_db()
        self.assertIsNotNone(self.staff.lastLoginAt)

    def test_login_non_digit_pin_rejected(self):
        res = self.client.post(self.url, {'email': 'staff@test.com', 'pin': 'abc123'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_short_pin_rejected(self):
        res = self.client.post(self.url, {'email': 'staff@test.com', 'pin': '123'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# 3. Staff CRUD — Admin only
# ---------------------------------------------------------------------------

class StaffCRUDTests(APITestCase):

    def setUp(self):
        self.admin = make_staff(email='admin@test.com', name='Admin', role=Staff.Roles.ADMIN, pin='000000')
        self.clerk = make_staff(email='clerk@test.com', name='Clerk', role=Staff.Roles.CLERK, pin='111111')
        self.admin_client = auth_client(self.admin)
        self.clerk_client = auth_client(self.clerk)
        self.list_url = reverse('accounts:staff-list')

    def test_admin_can_list_all_staff(self):
        res = self.admin_client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_clerk_cannot_list_staff(self):
        res = self.clerk_client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_staff(self):
        res = self.client.get(self.list_url)
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_admin_can_create_staff(self):
        payload = {
            'staffName': 'New Clerk', 'email': 'new@test.com',
            'pin': '222222', 'confirm_pin': '222222', 'role': Staff.Roles.CLERK
        }
        res = self.admin_client.post(self.list_url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Staff.objects.filter(email='new@test.com').exists())

    def test_clerk_cannot_create_staff(self):
        payload = {
            'staffName': 'Another', 'email': 'another@test.com',
            'pin': '333333', 'confirm_pin': '333333', 'role': Staff.Roles.CLERK
        }
        res = self.clerk_client.post(self.list_url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_mismatched_pins_rejected(self):
        payload = {
            'staffName': 'X', 'email': 'x@test.com',
            'pin': '123456', 'confirm_pin': '654321', 'role': Staff.Roles.CLERK
        }
        res = self.admin_client.post(self.list_url, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_non_digit_pin_rejected(self):
        payload = {
            'staffName': 'X', 'email': 'x@test.com',
            'pin': 'abcdef', 'confirm_pin': 'abcdef', 'role': Staff.Roles.CLERK
        }
        res = self.admin_client.post(self.list_url, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_delete_staff(self):
        url = reverse('accounts:staff-detail', args=[self.clerk.staffId])
        res = self.admin_client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_clerk_cannot_delete_staff(self):
        url = reverse('accounts:staff-detail', args=[self.admin.staffId])
        res = self.clerk_client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_clerk_cannot_change_own_role(self):
        url = reverse('accounts:staff-detail', args=[self.clerk.staffId])
        res = self.clerk_client.patch(url, {'role': Staff.Roles.ADMIN})
        self.assertNotEqual(res.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 4. Retrieve / Me endpoint
# ---------------------------------------------------------------------------

class StaffRetrieveTests(APITestCase):

    def setUp(self):
        self.admin = make_staff(email='admin@test.com', name='Admin', role=Staff.Roles.ADMIN, pin='000000')
        self.clerk = make_staff(email='clerk@test.com', name='Clerk', role=Staff.Roles.CLERK, pin='111111')
        self.admin_client = auth_client(self.admin)
        self.clerk_client = auth_client(self.clerk)

    def test_me_returns_own_data(self):
        url = reverse('accounts:staff-me')
        res = self.clerk_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['email'], 'clerk@test.com')

    def test_clerk_can_retrieve_own_profile(self):
        url = reverse('accounts:staff-detail', args=[self.clerk.staffId])
        res = self.clerk_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_clerk_cannot_retrieve_other_profile(self):
        url = reverse('accounts:staff-detail', args=[self.admin.staffId])
        res = self.clerk_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_retrieve_any_profile(self):
        url = reverse('accounts:staff-detail', args=[self.clerk.staffId])
        res = self.admin_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_unauthenticated_cannot_access_me(self):
        url = reverse('accounts:staff-me')
        res = self.client.get(url)
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


# ---------------------------------------------------------------------------
# 5. Change PIN Tests
# ---------------------------------------------------------------------------

class ChangePinTests(APITestCase):

    def setUp(self):
        self.admin = make_staff(email='admin@test.com', name='Admin', role=Staff.Roles.ADMIN, pin='000000')
        self.clerk = make_staff(email='clerk@test.com', name='Clerk', role=Staff.Roles.CLERK, pin='111111')
        self.admin_client = auth_client(self.admin)
        self.clerk_client = auth_client(self.clerk)

    def pin_url(self, staff):
        return reverse('accounts:staff-change-pin', args=[staff.staffId])

    def test_staff_can_change_own_pin(self):
        res = self.clerk_client.post(self.pin_url(self.clerk), {
            'old_pin': '111111', 'new_pin': '222222', 'confirm_new_pin': '222222'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.clerk.refresh_from_db()
        self.assertTrue(self.clerk.check_password('222222'))

    def test_wrong_old_pin_rejected(self):
        res = self.clerk_client.post(self.pin_url(self.clerk), {
            'old_pin': '999999', 'new_pin': '222222', 'confirm_new_pin': '222222'
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_pin_same_as_old_rejected(self):
        res = self.clerk_client.post(self.pin_url(self.clerk), {
            'old_pin': '111111', 'new_pin': '111111', 'confirm_new_pin': '111111'
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mismatched_new_pins_rejected(self):
        res = self.clerk_client.post(self.pin_url(self.clerk), {
            'old_pin': '111111', 'new_pin': '222222', 'confirm_new_pin': '333333'
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_cannot_change_another_staff_pin(self):
        other = make_staff(email='other@test.com', name='Other', pin='444444')
        res = self.clerk_client.post(self.pin_url(other), {
            'old_pin': '444444', 'new_pin': '555555', 'confirm_new_pin': '555555'
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_reset_any_pin_without_old_pin(self):
        res = self.admin_client.post(self.pin_url(self.clerk), {
            'old_pin': '', 'new_pin': '999999', 'confirm_new_pin': '999999'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.clerk.refresh_from_db()
        self.assertTrue(self.clerk.check_password('999999'))

    def test_admin_pin_reset_clears_lockout(self):
        self.clerk.failedPinAttempts = 5
        self.clerk.is_active = False
        self.clerk.save(update_fields=['failedPinAttempts', 'is_active'])
        self.admin_client.post(self.pin_url(self.clerk), {
            'old_pin': '', 'new_pin': '999999', 'confirm_new_pin': '999999'
        })
        self.clerk.refresh_from_db()
        self.assertEqual(self.clerk.failedPinAttempts, 0)


# ---------------------------------------------------------------------------
# 6. by_role and inactive endpoints
# ---------------------------------------------------------------------------

class FilterEndpointTests(APITestCase):

    def setUp(self):
        self.admin = make_staff(email='admin@test.com', name='Admin', role=Staff.Roles.ADMIN, pin='000000')
        self.clerk = make_staff(email='clerk@test.com', name='Clerk', role=Staff.Roles.CLERK, pin='111111')
        self.inactive = make_staff(email='gone@test.com', name='Gone', pin='222222', is_active=False)
        self.admin_client = auth_client(self.admin)
        self.clerk_client = auth_client(self.clerk)
        self.by_role_url = reverse('accounts:staff-by-role')
        self.inactive_url = reverse('accounts:staff-inactive')

    def test_by_role_returns_correct_staff(self):
        res = self.admin_client.get(self.by_role_url, {'role': Staff.Roles.CLERK})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        emails = [s['email'] for s in res.data]
        self.assertIn('clerk@test.com', emails)
        self.assertNotIn('admin@test.com', emails)

    def test_by_role_missing_param(self):
        res = self.admin_client.get(self.by_role_url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_by_role_invalid_role(self):
        res = self.admin_client.get(self.by_role_url, {'role': 'Wizard'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_clerk_cannot_access_by_role(self):
        res = self.clerk_client.get(self.by_role_url, {'role': Staff.Roles.CLERK})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_returns_only_inactive(self):
        res = self.admin_client.get(self.inactive_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        emails = [s['email'] for s in res.data]
        self.assertIn('gone@test.com', emails)
        self.assertNotIn('clerk@test.com', emails)

    def test_clerk_cannot_access_inactive(self):
        res = self.clerk_client.get(self.inactive_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
