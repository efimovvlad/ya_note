from django.test import TestCase
from django.urls import reverse
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from notes.models import Note
from notes.forms import NoteForm

User = get_user_model()


class TestContent(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.reader = User.objects.create(username='Читатель простой')
        cls.author = User.objects.create(username='Лев Толстой')
        cls.note = Note.objects.create(
            title='Заметка',
            text='Просто текст.',
            slug='note',
            author=cls.author
        )

    def test_notes_list_for_different_users(self):
        # Для каждой пары "пользователь - ожидаемый ответ"
        # перебираем имена тестируемых страниц:
        url = reverse('notes:list')
        users_statuses = (
            (self.author, True),
            (self.reader, False),
        )
        for user, status in users_statuses:
            # Логиним пользователя в клиенте:
            self.client.force_login(user)
            with self.subTest(user=user):
                url = reverse('notes:list')
                response = self.client.get(url)
                object_list = response.context['object_list']
                self.assertEqual(self.note in object_list, status)

    def test_pages_contains_form(self):
        urls = (
            ('notes:add', None),
            ('notes:edit', (self.note.slug,))
        )
        # Авторизуем клиент при помощи ранее созданного пользователя.
        self.client.force_login(self.author)
        for name, args in urls:
            url = reverse(name, args=args)
            response = self.client.get(url)
            self.assertIn('form', response.context)
            self.assertIsInstance(response.context['form'], NoteForm)
