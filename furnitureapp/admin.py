from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "room", "product_type", "price", "is_featured", "is_sample", "is_active")
    list_filter = ("room", "is_featured", "is_sample", "is_active")
    list_editable = ("price", "is_featured")
    search_fields = ("name", "product_type", "description")
    prepopulated_fields = {"slug": ("name",)}
