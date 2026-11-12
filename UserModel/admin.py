from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import  User, Profile

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display= ('id','username','email','first_name','last_name','profile','status', 'created_by','created_at','modified_by','modified_at')
    list_filter= ('status','profile','gender')
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
                    'emergency_contact_relationship','created_by','created_at','modified_by','modified_at','otp_code','otp_request_timestamps'
                )
            }),
    )
    add_fieldsets= UserAdmin.add_fieldsets+ (
        (None, {'fields': ('email','profile','status')}),
    )

admin.site.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display=('id','role','is_default')
    list_filter=('is_default')
    search_fields=('role',)


