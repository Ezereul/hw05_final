from http import HTTPStatus
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Post, Group, Comment, Follow


User = get_user_model()


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTest(TestCase):
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
        cls.author = User.objects.create(username='TestUser')
        cls.following = User.objects.create(username='following')
        cls.not_following = User.objects.create(username='not_following')
        cls.group = Group.objects.create(
            title='Название',
            slug='test-slug',
            description='Описание'
        )
        cls.post = Post.objects.create(
            text='Текст',
            author=cls.author,
            group=cls.group,
            image=uploaded
        )
        cls.comment = Comment.objects.create(
            text='Текст комментария',
            author=cls.author,
            post=cls.post
        )
        cls.index = 'posts:index'
        cls.group_list = 'posts:group_list'
        cls.profile = 'posts:profile'
        cls.post_detail = 'posts:post_detail'
        cls.post_create = 'posts:post_create'
        cls.post_edit = 'posts:post_edit'
        cls.follow_index = 'posts:follow_index'
        cls.profile_follow = 'posts:profile_follow'
        cls.profile_unfollow = 'posts:profile_unfollow'

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        cache.clear()

    def test_pages_uses_correct_templates(self):
        """URL-адрес использует соответсвующий шаблон."""
        templates_pages_names = {
            reverse(self.index): 'posts/index.html',
            reverse(self.group_list, args=[self.group.slug]):
                'posts/group_list.html',
            reverse(self.profile, args=[self.author.username]):
                'posts/profile.html',
            reverse(self.post_detail, args=[self.post.id]):
                'posts/post_detail.html',
            reverse(self.post_create): 'posts/post_create.html',
            reverse(self.post_edit, args=[self.post.id]):
                'posts/post_create.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_not_appear_in_other_group(self):
        """Пост не попадает на страницу группы, к которой не принадлежит."""
        test_group = Group.objects.create(
            title='Название 2',
            slug='other-slug',
            description='Описание'
        )

        response = self.authorized_client.get(reverse(
            self.group_list,
            args=[test_group.slug]))

        self.assertNotIn(self.post, response.context['page_obj'])

    def test_index_show_correct_context(self):
        """Страница 'posts:index' передает правильный контекст."""
        response = self.authorized_client.get(reverse(self.index))

        self.assertIn(self.post, response.context['page_obj'])

    def test_group_list_show_correct_context(self):
        """Страница 'posts:group_list' передает правильный контекст."""
        response = self.authorized_client.get(reverse(self.group_list,
                                                      args=[self.group.slug]))

        self.assertEqual(response.context['group'].slug, self.group.slug)
        self.assertIn(self.post, response.context['page_obj'])

    def test_profile_show_correct_context(self):
        """Страница 'posts:profile' передает правильный контекст."""
        count_posts = Post.objects.filter(author=self.author).count()

        response = self.authorized_client.get(reverse(
            self.profile,
            args=[self.author.username]))

        self.assertEqual(response.context['author'], self.author)
        self.assertEqual(response.context['count_posts'], count_posts)
        self.assertIn(self.post, response.context['page_obj'])

    def test_post_detail_show_correct_context(self):
        """Страница 'posts:post_detail' передает правильный контекст."""
        count_posts = Post.objects.filter(author=self.author).count()
        response = self.authorized_client.get(reverse(
            self.post_detail,
            args=[self.post.id]))
        post_context = response.context.get('post')

        self.assertEqual(post_context.text, 'Текст')
        self.assertEqual(post_context.author.username, 'TestUser')
        self.assertEqual(post_context.group.slug, 'test-slug')
        self.assertEqual(response.context['count_posts'], count_posts)

    def test_post_create_show_correct_context(self):
        """Страница 'posts:post_create' передает правильный контекст."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        response = self.authorized_client.get(reverse(self.post_create))
        for val, expected in form_fields.items():
            with self.subTest(val=val):
                form_field = response.context.get('form').fields.get(val)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Страница 'posts:post_edit' передает правильный контекст."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        response = self.authorized_client.get(reverse(self.post_edit,
                                                      args=[self.post.id]))

        self.assertTrue(response.context['is_edit'])
        for val, expected in form_fields.items():
            with self.subTest(val=val):
                form_field = response.context.get('form').fields.get(val)
                self.assertIsInstance(form_field, expected)

    def test_image_in_context_of_index_group_profile(self):
        """
        При выводе поста с картинкой изображение передается в словаре context.
        """
        addresses_with_img = (
            reverse(self.index),
            reverse(self.profile, args=[self.author]),
            reverse(self.group_list, args=[self.group.slug]),
        )

        for url in addresses_with_img:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)

                post = response.context['page_obj'][0]
                self.assertEqual(self.post.image, post.image)

    def test_image_in_context_of_post_detail(self):
        """
        Изображение передается в словаре context на страницу post_detail.
        """
        response = self.authorized_client.get(reverse(
            self.post_detail,
            args=[self.post.pk]))
        img = response.context['post'].image

        self.assertEqual(self.post.image, img)

    def test_comment_in_context(self):
        """Комментарий появляется на стринце поста."""
        response = self.authorized_client.get(reverse(
            self.post_detail, args=[self.post.id]))

        self.assertEqual(response.context['comments'][0], self.comment)

    def test_cache(self):
        """Проверка работы кэша."""
        new_post = Post.objects.create(
            text='Текст поста для кэша',
            author=self.author
        )
        response_before_cache = self.authorized_client.get(
            reverse(self.index))
        new_post.delete()
        response_cached = self.authorized_client.get(reverse(self.index))
        cache.clear()
        response_empty_cache = self.authorized_client.get(reverse(self.index))

        self.assertEqual(response_before_cache.content,
                         response_cached.content)
        self.assertNotEqual(response_before_cache.content,
                            response_empty_cache.content)

    def test_profile_follow_and_unfollow(self):
        """Пользователь может подписываться."""
        count_follows = Follow.objects.count()

        self.authorized_client.get(reverse(
            self.profile_follow,
            args=[self.following.username]))

        self.assertEqual(Follow.objects.count(), count_follows + 1)
        self.assertTrue(Follow.objects.filter(
            user=self.author, author=self.following).exists())

    def test_profile_unfollow(self):
        """Пользователь может отписываться."""
        count_follows = Follow.objects.count()
        Follow.objects.create(user=self.author,
                              author=self.following)

        self.authorized_client.get(reverse(
            self.profile_unfollow,
            args=[self.following.username]))

        self.assertEqual(Follow.objects.count(), count_follows)
        self.assertFalse(Follow.objects.filter(
            user=self.author, author=self.following).exists())

    def test_post_in_follow_index_of_follower(self):
        """Пост появляется в ленте тех, кто подписан."""
        post_in_follow = Post.objects.create(
            text='Текст поста из ленты подписок',
            author=self.following
        )
        Follow.objects.create(user=self.author, author=self.following)

        response = self.authorized_client.get(reverse(self.follow_index))

        self.assertIn(post_in_follow, response.context['page_obj'])

    def test_post_not_in_follow_index_of_not_follower(self):
        """Пост не появляется в ленте тех, кто не подписан."""
        post_not_in_follow = Post.objects.create(
            text='Текст поста',
            author=self.not_following
        )

        response = self.authorized_client.get(reverse(self.follow_index))

        self.assertNotIn(post_not_in_follow, response.context['page_obj'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='PagUser')
        cls.group = Group.objects.create(
            title='Название',
            slug='2test-slug',
            description='Описание'
        )
        cls.second_page_posts = 3
        for post_num in range(
                settings.POSTS_PER_PAGE + cls.second_page_posts):
            Post.objects.create(
                text=f'Текст {post_num+1}',
                author=cls.user,
                group=cls.group)
        cls.index = reverse('posts:index')
        cls.group_list = reverse('posts:group_list', args=[cls.group.slug])
        cls.profile = reverse('posts:profile', args=[cls.user.username])

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_first_pages_contains_ten_records(self):
        """Проверка первой страницы паджинатора."""
        pages = (
            self.index,
            self.group_list,
            self.profile,
        )
        for page in pages:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']),
                    settings.POSTS_PER_PAGE)

    def test_second_pages_contains_three_records(self):
        """Проверка второй страницы паджинатора."""
        pages = (
            self.index + '?page=2',
            self.group_list + '?page=2',
            self.profile + '?page=2',
        )
        for page in pages:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']),
                    self.second_page_posts)
