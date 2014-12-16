from django.contrib import admin
from mfiles_sync.models import Vault, View


@admin.register(Vault)
class VaultAdmin(admin.ModelAdmin):
    readonly_fields = ('guid',)
    list_display = ('name', 'guid')


@admin.register(View)
class ViewAdmin(admin.ModelAdmin):
    exclude = ('condition',)
    list_display = ('name', 'vault', 'is_enabled')
