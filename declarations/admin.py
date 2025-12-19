from django.contrib import admin
from .models import Declaration, DeclarationItem, MaterialProduct, HerstellerProfile, ProductWork


class ProductWorkInline(admin.TabularInline):
    model = ProductWork
    extra = 1
    fields = ['line_number', 'produktbezeichnung_arbeit', 'zahnnummer', 'zahnfarbe']


class DeclarationItemInline(admin.TabularInline):
    model = DeclarationItem
    extra = 1
    fields = ['line_number', 'material', 'firma', 'bestandteile', 'material_lot_no', 'ce_status']


@admin.register(Declaration)
class DeclarationAdmin(admin.ModelAdmin):
    list_display = ['declaration_number', 'praxis', 'created_at', 'item_count']
    list_filter = ['created_at', 'praxis']
    search_fields = ['declaration_number', 'praxis__username']
    inlines = [ProductWorkInline, DeclarationItemInline]
    readonly_fields = ['declaration_number', 'created_at', 'updated_at']

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Malzeme Sayısı'


@admin.register(ProductWork)
class ProductWorkAdmin(admin.ModelAdmin):
    list_display = ['declaration', 'line_number', 'produktbezeichnung_arbeit', 'zahnnummer', 'zahnfarbe']
    list_filter = ['declaration']
    search_fields = ['produktbezeichnung_arbeit', 'zahnnummer', 'zahnfarbe']


@admin.register(DeclarationItem)
class DeclarationItemAdmin(admin.ModelAdmin):
    list_display = ['declaration', 'line_number', 'material', 'firma', 'bestandteile', 'ce_status']
    list_filter = ['declaration', 'ce_status']
    search_fields = ['material', 'firma', 'bestandteile', 'material_lot_no']


@admin.register(MaterialProduct)
class MaterialProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'material', 'firma', 'bestandteile', 'material_lot_no', 'ce_status', 'is_active']
    list_filter = ['is_active', 'material', 'ce_status']
    search_fields = ['name', 'material', 'firma', 'bestandteile', 'material_lot_no']
    list_editable = ['is_active']


@admin.register(HerstellerProfile)
class HerstellerProfileAdmin(admin.ModelAdmin):
    list_display = ['firma_name', 'user', 'ort', 'telefon', 'email']
    search_fields = ['firma_name', 'ort', 'user__username']
