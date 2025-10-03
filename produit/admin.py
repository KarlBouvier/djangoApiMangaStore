from django.contrib import admin, messages
from django.contrib.auth.forms import User
from django.contrib.auth.models import send_mail

from .models import Manga, Tome, Commande, Category

class MangaAdmin(admin.ModelAdmin):
    list_display = ('ref', 'nom', 'prix', 'nombre_tome',)
    search_fields = ('nom', 'prix', 'categories__name')
    list_filter = ('categories',)
    filter_horizontal = ('categories',)

class TomeAdmin(admin.ModelAdmin):
    list_display = ('manga', 'numero', 'cover')
    search_fields = ('manga__nom',)
    
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('reference', 'utilisateur', 'statut', 'total_tomes', 'total_prix', 'date_creation', 'date_modification')
    search_fields = ('reference', 'utilisateur__username')
    list_filter = ('statut', 'date_creation', 'date_modification')
    readonly_fields = ('reference', 'utilisateur', 'statut', 'total_tomes', 'total_prix', 'date_creation', 'date_modification')
    ordering = ('-date_creation',)

admin.site.register(Manga, MangaAdmin)
admin.site.register(Tome, TomeAdmin)
admin.site.register(Commande, CommandeAdmin)
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {"slug": ("name",)}