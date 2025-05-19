from django.contrib import admin
from books.models import Author, Book

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name")
    search_fields = ("first_name", "last_name")

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "cover", "inventory", "daily_fee")
    list_filter = ("cover",)
    search_fields = ("title", "author__first_name", "author__last_name")