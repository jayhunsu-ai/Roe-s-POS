from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Staff


@admin.register(Staff)
class StaffAdmin(BaseUserAdmin):
    list_display = ['staffName', 'email', 'role', 'phone', 'is_active', 'createdAt']
    search_fields = ['staffName', 'email', 'phone']
    list_filter = ['role', 'is_active', 'createdAt']
    ordering = ['-createdAt']
    
    fieldsets = (
        ('Personal Info', {'fields': ('staffName', 'email', 'phone')}),
        ('Security', {'fields': ('password',)}),
        ('Role & Permissions', {'fields': ('role', 'is_staff', 'is_superuser', 'is_active')}),
        ('Important Dates', {'fields': ('createdAt', 'updatedAt'), 'classes': ('collapse',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('staffName', 'email', 'password1', 'password2', 'role'),
        }),
    )
    
    readonly_fields = ['createdAt', 'updatedAt', 'staffId']
    