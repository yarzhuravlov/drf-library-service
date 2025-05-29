from django.contrib import admin
from books.models import Author, Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "get_authors", "cover", "inventory", "daily_fee")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("authors")

    def get_authors(self, obj):
        return ", ".join(str(author) for author in obj.authors.all())
    get_authors.short_description = "Authors"


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name")
