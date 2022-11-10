from http import HTTPStatus
import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from ..models import Post, Group


User = get_user_model()


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
                     b'\x01\x00\x80\x00\x00\x00\x00\x00'
                     b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                     b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                     b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                     b'\x0A\x00\x3B')
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.author = User.objects.create(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
            image=uploaded
        )
        cls.index_url = '/'
        cls.post_edit_url = f'/posts/{cls.post.pk}/edit/'
        cls.post_create_url = '/create/'
        cls.group_list_url = f'/group/{cls.group.slug}/'
        cls.profile_url = f'/profile/{cls.author.username}/'
        cls.post_detail_url = f'/posts/{cls.post.pk}/'

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.not_author_client = Client()
        self.not_author = User.objects.create(username='NotAuthor')
        self.not_author_client.force_login(self.not_author)
        cache.clear()

    def test_urls_exists_at_desired_location(self):
        """Общедоступные страницы."""
        desired_locations = (
            self.index_url, self.group_list_url,
            self.profile_url,
            self.post_detail_url,
        )

        for url in desired_locations:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_url_exists_at_desired_location_authorize(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get(self.post_create_url)

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_url_redirect_anonymous_on_auth_login(self):
        """Страница /create/ перенаправляет анонимного пользователя."""
        response = self.guest_client.get(self.post_create_url, follow=True)

        self.assertRedirects(
            response, f'/auth/login/?next={self.post_create_url}'
        )

    def test_post_edit_url_exists_at_desired_location_author(self):
        """Страница /posts/<post_id>/edit/ доступна автору поста."""
        response = self.authorized_client.get(self.post_edit_url)

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_url_redirect_not_author(self):
        """Страница /posts/<post_id>/edit/ перенаправляет не автора поста."""
        response = self.not_author_client.get(
            self.post_edit_url,
            follow=True)

        self.assertRedirects(
            response, self.post_detail_url
        )

    def test_post_edit_url_redirect_anonymous_on_auth_login(self):
        """
        Страница /posts/<post_id>/edit/
        перенаправляет анонимного пользователя.
        """
        response = self.guest_client.get(self.post_edit_url)

        self.assertRedirects(
            response, f'/auth/login/?next={self.post_edit_url}'
        )

    def test_unexisting_page_return_404(self):
        """Запрос к несуществующей странице возращает ошибку 404."""
        response = self.guest_client.get('/unexisting/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            self.index_url: 'posts/index.html',
            self.group_list_url: 'posts/group_list.html',
            self.profile_url: 'posts/profile.html',
            self.post_detail_url: 'posts/post_detail.html',
            self.post_edit_url: 'posts/post_create.html',
            self.post_create_url: 'posts/post_create.html'
        }

        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
