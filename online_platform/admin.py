from django.contrib import admin
from django.utils.html import format_html
from .models import Product, NetworkUnit

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'model', 'release_date')
    search_fields = ('name', 'model')


@admin.action(description="Очистить задолженность перед поставщиком у выбранных")
def clear_debt(modeladmin, request, queryset):
    queryset.update(debt=0)


@admin.register(NetworkUnit)
class NetworkUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'country', 'supplier_link', 'debt', 'created_at', 'level_display')
    list_filter = ('city',)  # фильтр по названию города
    search_fields = ('name', 'city', 'country', 'email')
    actions = [clear_debt]
    filter_horizontal = ('products',)

    def supplier_link(self, obj):
        if obj.supplier:
            return format_html('<a href="/admin/online_platform/networkunit/{}/change/">{}</a>', obj.supplier.pk, obj.supplier)
        return "—"
    supplier_link.short_description = 'Поставщик'

    def level_display(self, obj):
        return obj.level
    level_display.short_description = 'Уровень'
