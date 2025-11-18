from django.contrib import admin
from .models import Author, Genre, Book, BookInstance


class BookInstanceInline(admin.TabularInline):
    """Дополнительно: inline для отображения экземпляров книг в книге"""
    model = BookInstance
    extra = 0


class BookInline(admin.TabularInline):
    """Встроенный список книг для автора"""
    model = Book
    extra = 0


class BookAdmin(admin.ModelAdmin):
    # Поля, которые будут отображаться в списке книг
    list_display = ('title', 'display_author', 'display_genre')

    # Поля для фильтрации
    list_filter = ('genre', 'author')

    # Поля для поиска
    search_fields = ('title', 'author__first_name', 'author__last_name')

    # Группировка полей в форме редактирования
    fieldsets = (
        (None, {
            'fields': ('title', 'author')
        }),
        ('Details', {
            'fields': ('summary', 'genre')
        }),
    )

    # Inline для отображения экземпляров книг
    inlines = [BookInstanceInline]

    # Предварительная загрузка связанных данных для оптимизации
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author').prefetch_related('genre')

    def display_author(self, obj):
        return str(obj.author) if obj.author else 'Не указан'

    def display_genre(self, obj):
        genres = obj.genre.all()
        if genres:
            return ', '.join(genre.name for genre in genres)
        return 'Не указаны'

    display_author.short_description = 'Автор'
    display_genre.short_description = 'Жанры'


class AuthorAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'date_of_birth', 'date_of_death')
    list_filter = ('date_of_birth', 'date_of_death')
    search_fields = ('last_name', 'first_name')
    fields = ['first_name', 'last_name', ('date_of_birth', 'date_of_death')]

    # ДОБАВЛЕНО: встроенный список книг для автора
    inlines = [BookInline]


class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(BookInstance)
class BookInstanceAdmin(admin.ModelAdmin):
    # ОБЪЕДИНЕНО: представление списка BookInstance
    list_display = ('book', 'status', 'borrower', 'due_back', 'id_display')
    list_filter = ('status', 'due_back')
    search_fields = ('book__title', 'imprint')

    fieldsets = (
        (None, {
            'fields': ('book', 'imprint', 'id')
        }),
        ('Availability', {
            'fields': ('status', 'due_back', 'borrower')
        }),
    )

    def id_display(self, obj):
        """Отображает ID книги"""
        return str(obj.id)

    id_display.short_description = 'ID экземпляра'


# Регистрация моделей в админке
admin.site.register(Book, BookAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Genre, GenreAdmin)