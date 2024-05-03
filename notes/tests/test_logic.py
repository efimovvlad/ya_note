from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from notes.forms import WARNING
from notes.models import Note
from pytils.translit import slugify

User = get_user_model()


class TestNoteCreation(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Адрес для добавления заметки и успешный урл.
        cls.url = reverse('notes:add',)
        cls.success_url = reverse('notes:success',)
        # Создаём пользователя и клиент, логинимся в клиенте.
        cls.user = User.objects.create(username='Мимо Крокодил')
        cls.auth_client = Client()
        cls.auth_client.force_login(cls.user)
        # Данные для POST-запроса при создании комментария.
        cls.form_data = {
            'title': 'Заметка',
            'text': 'Просто текст',
            'slug': 'note',
        }

    def test_user_can_create_note(self):
        # Совершаем запрос через авторизованный клиент.
        response = self.auth_client.post(self.url, data=self.form_data)
        # Проверяем, что редирект привёл на страницу успешного урл.
        self.assertRedirects(response, self.success_url)
        # Считаем количество заметок.
        notes_count = Note.objects.count()
        # Убеждаемся, что есть одна заметка.
        self.assertEqual(notes_count, 1)
        # Получаем объект заметки из базы.
        note = Note.objects.get()
        # Проверяем, что все атрибуты заметки совпадают с ожидаемыми.
        self.assertEqual(note.title, self.form_data['title'])
        self.assertEqual(note.text, self.form_data['text'])
        self.assertEqual(note.slug, self.form_data['slug'])
        self.assertEqual(note.author, self.user)

    def test_anonymous_user_cant_create_note(self):
        # Совершаем запрос от анонимного клиента, в POST-запросе отправляем
        # предварительно подготовленные данные формы.
        self.client.post(self.url, data=self.form_data)
        # Считаем количество заметок.
        notes_count = Note.objects.count()
        # Ожидаем, что заметок в базе нет - сравниваем с нулём.
        self.assertEqual(notes_count, 0)

    def test_not_unique_slug(self):
        # Создаем первую заметку
        self.auth_client.post(self.url, data=self.form_data)
        # Формируем данные для отправки формы; форма включает
        # такой же слаг как у первой заметки.
        response = self.auth_client.post(self.url, data=self.form_data)
        # Проверяем, есть ли в ответе ошибка формы.
        slug = self.form_data['slug']
        self.assertFormError(
            response,
            form='form',
            field='slug',
            errors=f'{slug}{WARNING}'
        )
        # Дополнительно убедимся, что заметка не была создана.
        comments_count = Note.objects.count()
        self.assertEqual(comments_count, 1)

    def test_empty_slug(self):
        url = reverse('notes:add')
        # Убираем поле slug из словаря:
        self.form_data.pop('slug')
        response = self.auth_client.post(url, data=self.form_data)
        # Проверяем, что даже без slug заметка была создана:
        self.assertRedirects(response, reverse('notes:success'))
        self.assertEqual(Note.objects.count(), 1)
        # Получаем созданную заметку из базы:
        new_note = Note.objects.get()
        # Формируем ожидаемый slug:
        expected_slug = slugify(self.form_data['title'])
        # Проверяем, что slug заметки соответствует ожидаемому:
        self.assertEqual(new_note.slug, expected_slug)


class TestNoteEditDelete(TestCase):
    # Тексты для заметок не нужно дополнительно создавать
    # (в отличие от объектов в БД), им не нужны ссылки на self или cls,
    # поэтому их можно перечислить просто в атрибутах класса.
    TITLE = 'Заметка'
    NOTE_TEXT = 'Просто текст'
    SLUG = 'note'
    NEW_TITLE = 'Новый заголовок'
    NEW_NOTE_TEXT = 'Обновлённый текст'
    NEW_SLUG = 'test'

    @classmethod
    def setUpTestData(cls):
        # Создаём заметку в БД.
        cls.author = User.objects.create(username='Лев Толстой')
        cls.note = Note.objects.create(
            title=cls.TITLE,
            text=cls.NOTE_TEXT,
            slug=cls.SLUG,
            author=cls.author
        )
        # Формируем адрес блока с заметкой, который понадобится для тестов.
        cls.success_url = reverse('notes:success')
        # Создаём клиент для пользователя-автора.
        cls.author_client = Client()
        # "Логиним" пользователя в клиенте.
        cls.author_client.force_login(cls.author)
        # Делаем всё то же самое для пользователя-читателя.
        cls.reader = User.objects.create(username='Читатель')
        cls.reader_client = Client()
        cls.reader_client.force_login(cls.reader)
        # URL для редактирования заметки.
        cls.edit_url = reverse('notes:edit', args=(cls.note.slug,))
        # URL для удаления заметки.
        cls.delete_url = reverse('notes:delete', args=(cls.note.slug,))
        # Формируем данные для POST-запроса по обновлению заметки.
        cls.form_data = {
            'title': cls.NEW_TITLE,
            'text': cls.NEW_NOTE_TEXT,
            'slug': cls.NEW_SLUG,
        }

    def test_author_can_edit_note(self):
        # Выполняем запрос на редактирование от имени автора заметки.
        response = self.author_client.post(self.edit_url, data=self.form_data)
        # Проверяем, что сработал редирект.
        self.assertRedirects(response, self.success_url)
        # Обновляем объект заметки.
        self.note.refresh_from_db()
        # Проверяем, что текст заметки соответствует обновленному.
        self.assertEqual(self.note.title, self.NEW_TITLE)
        self.assertEqual(self.note.text, self.NEW_NOTE_TEXT)
        self.assertEqual(self.note.slug, self.NEW_SLUG)

    def test_other_user_cant_edit_note(self):
        # Выполняем запрос на редактирование от имени другого пользователя.
        response = self.reader_client.post(self.edit_url, data=self.form_data)
        # Проверяем, что вернулась 404 ошибка.
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        # Обновляем объект заметки.
        self.note.refresh_from_db()
        # Проверяем, что текст остался тем же, что и был.
        self.assertEqual(self.note.title, self.TITLE)
        self.assertEqual(self.note.text, self.NOTE_TEXT)
        self.assertEqual(self.note.slug, self.SLUG)

    def test_author_can_delete_note(self):
        # От имени автора заметки отправляем DELETE-запрос на удаление.
        response = self.author_client.delete(self.delete_url)
        # Проверяем, что редирект привёл к успешному урлу.
        # Заодно проверим статус-коды ответов.
        self.assertRedirects(response, self.success_url)
        # Считаем количество заметок в системе.
        notes_count = Note.objects.count()
        # Ожидаем ноль заметок в системе.
        self.assertEqual(notes_count, 0)

    def test_user_cant_delete_note_of_another_user(self):
        # Выполняем запрос на удаление от пользователя-читателя.
        response = self.reader_client.delete(self.delete_url)
        # Проверяем, что вернулась 404 ошибка.
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        # Убедимся, что заметка по-прежнему на месте.
        comments_count = Note.objects.count()
        self.assertEqual(comments_count, 1)
