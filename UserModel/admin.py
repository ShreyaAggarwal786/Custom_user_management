from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import OTP, User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display= ('id','username','email','profiles','status', 'is_staff')
    list_filter= ('status','profiles','is_staff')
    search_fields = ('username','email','first_name', 'last_name')
    ordering=('id',)

    fieldsets= UserAdmin.fieldsets + (
        (
            "Extra details",
            {
                'fields':(
                    'profiles','status','date_of_birth','gender',
                    'nationality','image','blood_group','phone',
                    'permanent_address','current_address',
                    'emergency_contact_name','emergency_contact_number',
                    'emergency_contact_relationship',
                )
            },
        ),
    )
    add_fieldsets= UserAdmin.add_fieldsets+ (
        (None, {'fields': ('email','profiles','status')}),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display=('id','user','purpose','is_used','attempts','created_at','expires_at')
    list_filter= ('purpose','is_used')
    readonly_fields= ('created_at',)
