from django.test import TestCase
from django.contrib.auth.models import User, Permission
from django.urls import reverse
import datetime
import uuid
from django.utils import timezone
from . import models


class LoanedBookInstancesByUserListViewTest(TestCase):

    def setUp(self):
        # Создание двух пользователей
        self.test_user1 = User.objects.create_user(username='testuser1', password='12345')
        self.test_user1.save()
        self.test_user2 = User.objects.create_user(username='testuser2', password='12345')
        self.test_user2.save()

        # Создание книги
        test_author = Author.objects.create(first_name='John', last_name='Smith')
        test_genre = Genre.objects.create(name='Fantasy')
        test_book = Book.objects.create(
            title='Book Title',
            summary='My book summary',
            isbn='ABCDEFG',
            author=test_author,
        )
        # Create genre as a post-step
        genre_objects_for_book = Genre.objects.all()
        test_book.genre.set(genre_objects_for_book)
        test_book.save()

        # Создание объектов BookInstance с правильным статусом
        number_of_book_copies = 10
        for book_copy in range(number_of_book_copies):
            return_date = timezone.now() + datetime.timedelta(days=book_copy % 5)
            if book_copy % 2:
                the_borrower = self.test_user1
                status = 'o'  # On loan - для тестового пользователя
            else:
                the_borrower = self.test_user2
                status = 'm'  # Maintenance - для другого пользователя
            BookInstance.objects.create(
                book=test_book,
                imprint='Unlikely Imprint, 2016',
                due_back=return_date,
                borrower=the_borrower,
                status=status
            )

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('my-borrowed'))
        self.assertRedirects(resp, '/accounts/login/?next=/catalog/mybooks/')

    def test_logged_in_uses_correct_template(self):
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(resp.context['user']), 'testuser1')
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'catalog/bookinstance_list_borrowed_user.html')

    def test_only_borrowed_books_in_list(self):
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(resp.context['user']), 'testuser1')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('bookinstance_list' in resp.context)

        # Проверяем, что только книги со статусом 'o' и правильным заемщиком
        borrowed_books = resp.context['bookinstance_list']
        for book in borrowed_books:
            self.assertEqual(book.status, 'o')
            self.assertEqual(book.borrower.username, 'testuser1')

    def test_borrowed_books_count(self):
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(resp.context['user']), 'testuser1')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('bookinstance_list' in resp.context)

        # Проверка, что изначально у нас нет книг в списке
        self.assertEqual(len(resp.context['bookinstance_list']), 0)

        # Теперь все книги "взяты на прокат"
        get_ten_books = BookInstance.objects.all()[:10]

        for copy in get_ten_books:
            copy.status = 'o'
            copy.save()

        # Проверка, что все забронированные книги в списке
        resp = self.client.get(reverse('my-borrowed'))
        self.assertEqual(str(resp.context['user']), 'testuser1')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('bookinstance_list' in resp.context)

        # Подтверждение, что все книги принадлежат testuser1 и взяты "на прокат"
        for bookitem in resp.context['bookinstance_list']:
            self.assertEqual(resp.context['user'], bookitem.borrower)
            self.assertEqual('o', bookitem.status)

    def test_pages_ordered_by_due_date(self):
        # Изменение статуса на "в прокате"
        for copy in BookInstance.objects.all():
            copy.status = 'o'
            copy.save()

        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))

        # Пользователь залогинился
        self.assertEqual(str(resp.context['user']), 'testuser1')
        self.assertEqual(resp.status_code, 200)

        # Подтверждение, что из всего списка показывается только 10 экземпляров
        self.assertEqual(len(resp.context['bookinstance_list']), 10)

        last_date = 0
        for copy in resp.context['bookinstance_list']:
            if last_date == 0:
                last_date = copy.due_back
            else:
                self.assertTrue(last_date <= copy.due_back)


class RenewBookInstancesViewTest(TestCase):

    def setUp(self):
        # Создание пользователя
        test_user1 = User.objects.create_user(username='testuser1', password='12345')
        test_user1.save()

        test_user2 = User.objects.create_user(username='testuser2', password='12345')
        test_user2.save()

        # Добавление разрешения
        permission = Permission.objects.get(codename='can_mark_returned')
        test_user2.user_permissions.add(permission)
        test_user2.save()

        # Создание книги
        test_author = Author.objects.create(first_name='John', last_name='Smith')
        test_genre = Genre.objects.create(name='Fantasy')
        test_book = Book.objects.create(
            title='Book Title',
            summary='My book summary',
            isbn='ABCDEFG',
            author=test_author
        )

        # Создание жанра
        genre_objects_for_book = Genre.objects.all()
        test_book.genre.set(genre_objects_for_book)
        test_book.save()

        # Создание объекта BookInstance для пользователя test_user1
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance1 = BookInstance.objects.create(
            book=test_book,
            imprint='Unlikely Imprint, 2016',
            due_back=return_date,
            borrower=test_user1,
            status='o'
        )

        # Создание объекта BookInstance для пользователя test_user2
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance2 = BookInstance.objects.create(
            book=test_book,
            imprint='Unlikely Imprint, 2016',
            due_back=return_date,
            borrower=test_user2,
            status='o'
        )

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        # Manually check redirect (Can't use assertRedirect, because the redirect URL is unpredictable)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/'))

    def test_redirect_if_logged_in_but_not_correct_permission(self):
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))

        # Manually check redirect (Can't use assertRedirect, because the redirect URL is unpredictable)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/'))

    def test_logged_in_with_permission_borrowed_book(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance2.pk}))

        # Check that it lets us login - this is our book and we have the right permissions.
        self.assertEqual(resp.status_code, 200)

    def test_logged_in_with_permission_another_users_borrowed_book(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))

        # Check that it lets us login. We're a librarian, so we can view any users book
        self.assertEqual(resp.status_code, 200)

    def test_HTTP404_for_invalid_book_if_logged_in(self):
        test_uid = uuid.uuid4()  # unlikely UID to match our bookinstance!
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': test_uid}))
        self.assertEqual(resp.status_code, 404)

    def test_uses_correct_template(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        self.assertEqual(resp.status_code, 200)

        # Check we used correct template
        self.assertTemplateUsed(resp, 'catalog/book_renew_librarian.html')

    def test_form_renewal_date_initially_has_date_three_weeks_in_future(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        self.assertEqual(resp.status_code, 200)

        date_3_weeks_in_future = datetime.date.today() + datetime.timedelta(weeks=3)
        self.assertEqual(resp.context['form'].initial['renewal_date'], date_3_weeks_in_future)

    def test_form_renewal_date_initially_has_date_three_weeks_in_future_alternative(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        self.assertEqual(resp.status_code, 200)

        date_3_weeks_in_future = datetime.date.today() + datetime.timedelta(weeks=3)
        self.assertEqual(resp.context['form'].initial['renewal_date'], date_3_weeks_in_future)

    def test_redirects_to_all_borrowed_book_list_on_success(self):
        login = self.client.login(username='testuser2', password='12345')
        valid_date_in_future = datetime.date.today() + datetime.timedelta(weeks=2)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}),
                                {'renewal_date': valid_date_in_future})
        self.assertRedirects(resp, reverse('all-borrowed'))

    def test_form_invalid_renewal_date_past(self):
        login = self.client.login(username='testuser2', password='12345')
        date_in_past = datetime.date.today() - datetime.timedelta(weeks=1)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}),
                                {'renewal_date': date_in_past})
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp, 'form', 'renewal_date', 'Invalid date - renewal in past')

    def test_form_invalid_renewal_date_future(self):
        login = self.client.login(username='testuser2', password='12345')
        invalid_date_in_future = datetime.date.today() + datetime.timedelta(weeks=5)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}),
                                {'renewal_date': invalid_date_in_future})
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp, 'form', 'renewal_date', 'Invalid date - renewal more than 4 weeks ahead')


class AuthorCreateViewTest(TestCase):

    def setUp(self):
        # Создание пользователей
        self.test_user1 = User.objects.create_user(username='testuser1', password='12345')
        self.test_user1.save()

        self.test_user2 = User.objects.create_user(username='testuser2', password='12345')
        self.test_user2.save()

        # Добавление разрешения для test_user2
        permission = Permission.objects.get(codename='can_mark_returned')
        self.test_user2.user_permissions.add(permission)
        self.test_user2.save()

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('author-create'))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/'))

    def test_forbidden_if_logged_in_but_not_correct_permission(self):
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('author-create'))
        self.assertEqual(resp.status_code, 403)

    def test_logged_in_with_permission(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('author-create'))
        self.assertEqual(resp.status_code, 200)

    def test_uses_correct_template(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('author-create'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'catalog/author_form.html')

    def test_initial_date_of_death(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('author-create'))
        self.assertEqual(resp.status_code, 200)

        # Проверяем начальное значение даты смерти
        expected_initial_date = '12/10/2016'
        self.assertEqual(resp.context['form'].initial['date_of_death'], expected_initial_date)

    def test_redirects_to_author_detail_on_success(self):
        login = self.client.login(username='testuser2', password='12345')

        # Данные для создания автора
        author_data = {
            'first_name': 'Test',
            'last_name': 'Author',
            'date_of_birth': '1980-01-01',
            'date_of_death': '2020-01-01',
        }

        resp = self.client.post(reverse('author-create'), author_data)

        # Проверяем, что создался автор
        self.assertEqual(Author.objects.count(), 1)
        new_author = Author.objects.first()

        # Проверяем редирект на страницу деталей автора
        self.assertRedirects(resp, reverse('author-detail', kwargs={'pk': new_author.pk}))

    def test_form_validation(self):
        login = self.client.login(username='testuser2', password='12345')

        # Пытаемся создать автора без обязательных полей
        invalid_data = {
            'first_name': '',  # Пустое обязательное поле
            'last_name': 'Author',
        }

        resp = self.client.post(reverse('author-create'), invalid_data)
        self.assertEqual(resp.status_code, 200)
        # Проверяем, что форма содержит ошибки
        self.assertTrue(resp.context['form'].errors)