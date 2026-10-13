from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

PASSWORD = 'Str0ngPass!234'


from accounts.models import Profile

class ProfileSignalTests(TestCase):
    def test_profile_created_automatically(self):
        user = User.objects.create_user('alice', 'alice@example.com', PASSWORD)
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(Profile.objects.get(user=user).role, 'member')

class RegistrationTests(TestCase):
    def valid_data(self, **extra):
        data = {
            'username': 'bob',
            'first_name': 'Bob',
            'last_name': 'Smith',
            'email': 'bob@example.com',
            'password1': PASSWORD,
            'password2': PASSWORD,
            'role': 'manager',
        }
        data.update(extra)
        return data

    def test_register_creates_user_with_chosen_role(self):
        response = self.client.post(reverse('register'), self.valid_data())
        self.assertRedirects(response, reverse('profile'))
        user = User.objects.get(username='bob')
        self.assertEqual(user.profile.role, 'manager')

    def test_password_is_hashed_not_stored_as_plain_text(self):
        self.client.post(reverse('register'), self.valid_data())
        user = User.objects.get(username='bob')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_weak_password_rejected(self):
        response = self.client.post(
            reverse('register'), self.valid_data(password1='12345', password2='12345')
        )
        self.assertEqual(response.status_code, 200)  # form shown again with errors
        self.assertFalse(User.objects.filter(username='bob').exists())

    def test_duplicate_email_rejected(self):
        User.objects.create_user('old', 'bob@example.com', PASSWORD)
        response = self.client.post(reverse('register'), self.valid_data())
        self.assertContains(response, 'already exists')
        self.assertFalse(User.objects.filter(username='bob').exists())


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('carol', 'carol@example.com', PASSWORD)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('profile')}")

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(reverse('login'), {'username': 'carol', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_then_logout(self):
        self.client.post(reverse('login'), {'username': 'carol', 'password': PASSWORD})
        self.assertIn('_auth_user_id', self.client.session)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_profile_update(self):
        self.client.login(username='carol', password=PASSWORD)
        self.client.post(reverse('profile'), {
            'first_name': 'Carol', 'last_name': 'J', 'email': 'carol@example.com',
            'phone': '9999999999', 'bio': 'Hello',
        })
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, '9999999999')