from unittest import TestCase
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache.backends import locmem
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile

from PIL import Image
import tempfile

from posts.models import Post, User, Group


TEST_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}


@override_settings(CACHES=TEST_CACHE)
class ProfileTest(TestCase):

    def _create_image(self):
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            image = Image.new('RGB', (200, 200), 'white')
            image.save(f, 'PNG')
        return open(f.name, mode='rb')

    def _create_file(self):
        file = SimpleUploadedFile('filename.txt', b'hello world', 'text/plain')
        return file

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='sarah', email='connor.s@skynet.com', password='12345')
        self.group = Group.objects.create(
            title='test-group',
            slug='test-group',
            description='test-group',
        )

    def test_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('profile', kwargs={'username': self.user.username}))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['author'], User)
        self.assertEqual(
            response.context['author'].username, self.user.username)

    def test_auth_user_can_publish_post(self):
        self.client.force_login(self.user)
        self.post = Post.objects.create(text='Новый пост', author=self.user)
        response = self.client.get(
            reverse('profile', kwargs={'username': self.user.username}))
        self.assertEqual(Post.objects.count(), 1)

    def test_unauth_user_cant_publish_post(self):
        response = self.client.post(
            reverse('new_post'),
            data={'group': '', 'text': 'Новый пост'},
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/new/')
        self.assertEqual(Post.objects.all().count(), 0)

    def url_check(self, post):
        urls = [
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post', kwargs={
                    'username': self.user.username, 'post_id': self.post.id})
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertContains(response, self.post.text)

    def test_post_appears_on_pages(self):
        self.client.force_login(self.user)
        self.post = Post.objects.create(text='Новый пост', author=self.user)
        self.assertEqual(self.post.text, 'Новый пост')
        self.url_check(self.post)

    def test_unauth_user_cant_edit_post(self):
        self.client.force_login(self.user)
        self.post = Post.objects.create(text='Новый пост', author=self.user)
        response = self.client.get(
            reverse(
                'post_edit',
                kwargs={
                    'username': self.user.username,
                    'post_id': self.post.id
                }
            )
        )
        self.assertEqual(response.status_code, 200)
        self.client.post(
            reverse(
                'post_edit',
                kwargs={
                    'username': self.user.username,
                    'post_id': self.post.id
                }
            ),
            {'text': 'Измененный текст'}
        )
        self.post.refresh_from_db()
        self.assertEqual(self.post.text, 'Измененный текст')
        self.url_check(self.post)

    def test_page_error_404(self):
        response = self.client.get('/404/')
        self.assertEqual(response.status_code, 404)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_image_upload(self):
        self.client.force_login(self.user)
        self.post = Post.objects.create(
            text='Новый пост',
            author=self.user)
        self.image = self._create_image()
        urls = [
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post', kwargs={
                    'username': self.user.username, 'post_id': self.post.id})
        ]
        response = self.client.post(
            reverse(
                'post_edit',
                kwargs={
                    'username': self.user.username,
                    'post_id': self.post.id
                }
            ),
            {'text': self.post.text, 'image': self.image})
        self.assertRedirects(response, urls[2])
        for url in urls:
            response = self.client.get(url)
            self.assertContains(response, '<img')

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_image_non_upload(self):
        self.client.force_login(self.user)
        self.post = Post.objects.create(
            text='Новый пост',
            author=self.user)
        self.file = self._create_file()
        response = self.client.post(
            reverse(
                'post_edit',
                kwargs={
                    'username': self.user.username,
                    'post_id': self.post.id
                }
            ),
            {'text': self.post.text, 'image': self.file})
        self.assertTrue(response.context['form'].has_error('image'))


class TestCache(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='sarah', email='connor.s@skynet.com', password='12345')

    def test_index_page_cache_key(self):
        self.client.force_login(self.user)
        self.post = Post.objects.create(text='Новый пост1', author=self.user)
        key = make_template_fragment_key('index_page', [1])
        self.client.get(reverse('index'))
        self.assertTrue(bool(cache.get(key)))
        cache.clear()
        self.assertFalse(bool(cache.get(key)))

    def test_index_page_cache(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('index'))
        self.post = Post.objects.create(text='Новый пост2', author=self.user)
        self.assertNotContains(response, 'Новый пост2')
        cache.clear()
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Новый пост2')


@override_settings(CACHES=TEST_CACHE)
class FollowTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='sarah', email='connor.s@skynet.com', password='12345')
        self.user1 = User.objects.create_user(
            username='terminator', email='terminator@skynet.com', password='12345')
        self.user2 = User.objects.create_user(
            username='zhidkiy_terminator', email='zhidkiy_terminator@skynet.com', password='12345')

    def test_user_can_follow_unfollow(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                'profile_follow', kwargs={'username': self.user1.username}
            ),
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse(
                'profile_unfollow', kwargs={'username': self.user1.username}
            ),
            follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_user_can_follow_post(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                'profile_follow', kwargs={'username': self.user.username}
            ),
            follow=True
        )
        self.post = Post.objects.create(text='Новый пост', author=self.user)
        self.client.logout()

        self.client.force_login(self.user1)
        response = self.client.get(
            reverse(
                'profile_follow', kwargs={'username': self.user.username}
            ),
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.user1)
        response = self.client.get(
            reverse('follow_index'),
            follow=True
        )
        self.assertContains(response, 'Новый пост')
        self.client.logout()

        self.client.force_login(self.user2)
        response = self.client.get(
            reverse('follow_index'),
            follow=True
        )
        self.assertNotContains(response, 'Новый пост')
