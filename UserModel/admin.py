from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import  User, Profile

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display= ('id','username','email','profile','status', 'is_staff')
    list_filter= ('status','profile','is_staff')
    search_fields = ('username','email','first_name', 'last_name')
    ordering=('id',)

    fieldsets= UserAdmin.fieldsets + (
        (
            "Extra details",
            {
                'fields':(
                    'profile','status','date_of_birth','gender',
                    'nationality','image','blood_group','phone',
                    'permanent_address','current_address',
                    'emergency_contact_name','emergency_contact_number',
                    'emergency_contact_relationship',
                )
            },
        ),
    )
    add_fieldsets= UserAdmin.add_fieldsets+ (
        (None, {'fields': ('email','profile','status')}),
    )

admin.site.register(Profile)


