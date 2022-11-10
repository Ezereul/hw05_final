from http import HTTPStatus
import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from ..models import Post, Comment


User = get_user_model()


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.post = Post.objects.create(
            text='Text',
            author=cls.user
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_post_create(self):
        """Авторизованный пользователь может создать пост."""
        count_posts = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'author': self.user,
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, reverse('posts:profile',
                                               args=[self.user.username]))
        self.assertEqual(Post.objects.count(), count_posts + 1)
        self.assertTrue(Post.objects.filter(
            text=form_data['text'],
            author=form_data['author'],
            group=None).exists())

    def test_guest_cant_create_post(self):
        """
        Анонимный пользователь не может создать пост и перенаправляется
        на страницу авторизации.
        """
        count_posts = Post.objects.count()
        form_data = {
            'text': 'text',
            'author': ''
        }

        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, '/auth/login/?next=/create/')
        self.assertFalse(Post.objects.filter(text='text').exists())
        self.assertEqual(Post.objects.count(), count_posts)

    def test_cant_create_empty_post(self):
        """Пользователь не может создать пустой пост."""
        count_posts = Post.objects.count()
        form_data = {
            'text': '',
            'author': self.user
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertEqual(Post.objects.count(), count_posts)
        self.assertFormError(
            response,
            'form',
            'text',
            'Обязательное поле.'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit(self):
        """Пользователь может редактировать пост."""
        count_posts = Post.objects.count()
        form_data = {
            'text': 'Отредактированный',
            'author': self.user
        }

        response = self.authorized_client.post(
            reverse('posts:post_edit', args=[self.post.id]),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, reverse('posts:post_detail',
                                               args=[self.post.id]))
        self.assertTrue(Post.objects.filter(
            text=form_data['text'],
            author=form_data['author'],
            group=None).exists())
        self.assertEqual(Post.objects.count(), count_posts)

    def test_create_post_with_image(self):
        """При создании поста с картинкой, пост добавляется в базу данных."""
        count_posts = Post.objects.count()
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
        form_data = {
            'text': 'Текст поста с картинкой',
            'author': self.user,
            'image': uploaded,
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        post_image = Post.objects.get(text=form_data['text']).image

        self.assertRedirects(response, reverse('posts:profile',
                                               args=[self.user.username]))
        self.assertEqual(Post.objects.count(), count_posts + 1)
        self.assertTrue(Post.objects.filter(
            text=form_data['text'],
            author=form_data['author'],
            image=post_image,
            group=None
        ).exists())

    def test_authorized_can_add_comment(self):
        """Авторизованный пользователь может добавить комментарий."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
            'author': self.user
        }

        response = self.authorized_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response, reverse('posts:post_detail', args=[self.post.id]))
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text'],
                author=form_data['author'],
                post=self.post.pk).exists()
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)

    def test_guest_cant_add_comment(self):
        """Неавторизованный пользователь не может добавить комментарий."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
            'author': self.user
        }

        response = self.guest_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.id}/comment')
        self.assertFalse(
            Comment.objects.filter(text=form_data['text']).exists())
        self.assertEqual(Comment.objects.count(), comments_count)
