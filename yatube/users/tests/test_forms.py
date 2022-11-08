from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse


User = get_user_model()


class UserSignupFormTest(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_signup(self):
        count_users = User.objects.count()
        form_data = {
            'first_name': 'Alex',
            'last_name': 'Levin',
            'username': 'Nix',
            'email': 'nix@gmail.com',
            'password1': 'testingpasswordFORuser1',
            'password2': 'testingpasswordFORuser1'
        }
        response = self.guest_client.post(
            reverse('users:signup'),
            data=form_data,
            follow=True
        )
        self.assertEqual(User.objects.count(), count_users + 1)
        self.assertRedirects(response, '/')
