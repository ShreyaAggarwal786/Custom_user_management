from django.contrib.auth.models import AbstractUser
from django.db import models


import secrets 
from datetime import timedelta
from django.conf import settings
from django.utils import timezone


class User(AbstractUser):
    class Profile(models.TextChoices):
        ADMINISTRATOR= "administrator", "Administrator"
        STANDARD= "standard", "Standard"
        DEVELOPER= "developer", "Developer"
        CLIENT= "client", "Client"
        HUMAN_RESOURCES= "human_Resources", "Human_Resources"

    class Status(models.TextChoices):
        ACTIVE= "active", "Active"
        INACTIVE= "inactive", "Inactive"

    class Gender(models.TextChoices):
        FEMALE= "female","Female"
        MALE= "male","Male"
        OTHER= "other", "Other"

    class Blood_Group(models.TextChoices):
        A_POSITIVE= "A+","A+"
        A_NEGATIVE= "A-","A-"
        B_POSITIVE= "B+", "B+"
        B_NEGATIVE= "B-","B-"
        AB_POSITIVE= "AB+", "AB+"
        AB_NEGATIVE= "AB-","AB-"
        O_POSITIVE= "O+","O+"
        O_NEGATIVE= "O-","O-"

    email= models.EmailField(unique= True)
    profiles= models.CharField(max_length= 20, choices=Profile.choices, default= Profile.STANDARD)
    date_of_birth= models.DateField(blank=True, null=True )
    gender= models.CharField(max_length=10, choices=Gender.choices, blank= True)
    nationality= models.CharField(max_length= 70,blank=True)
    image= models.ImageField(upload_to= "Profile_images/", null= True, blank=True)
    blood_group= models.CharField(max_length=3, choices=Blood_Group.choices, blank=True)
    phone= models.CharField(max_length=12,blank= True)
    permanent_address= models.TextField( blank=True)
    current_address=models.TextField( blank=True)
    emergency_contact_name= models.CharField(max_length=50, blank=True)
    emergency_contact_number= models.CharField(max_length=12, blank= True)
    emergency_contact_relationship= models.CharField(max_length= 50, blank=True)
    status= models.CharField(max_length=10, choices=Status.choices, default= Status.ACTIVE)

    def __str__(self):
        return self.email

class OTP(models.Model):
    class Purpose(models.TextChoices):
        VERIFY = "verify", "Verify"
        PASSWORD_RESET = "password_reset", "Password Reset"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps"
    )
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.code:
                self.code = f"{secrets.randbelow(1_000_000):06d}"
            if not self.expires_at:
                self.expires_at = timezone.now() + timedelta(
                    minutes=settings.OTP_EXPIRY_MINUTES
                )
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"{self.user.email} - {self.purpose}"




class Client(models.Model):
    class Status(models.TextChoices):
        ACTIVE="active","Active"
        INACTIVE="inactive","Inactive"


    first_name= models.CharField(max_length=100)
    last_name= models.CharField(max_length=100)
    email= models.EmailField(max_length=254, unique=True)
    contact_number=models.CharField(max_length=15)
    address=models.TextField()
    country= models.CharField(max_length=100)
    status= models.CharField(max_length=10, choices= Status.choices, default=Status.ACTIVE)


    created_by= models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete= models.PROTECT,
        related_name="clients_created"
    )


    # created_by=models.CharField(max_length=254, null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    modified_by= models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clients_modified"
    )

    # modified_by= models.CharField(max_length=254,null=True.blank=True)
    modified_at=models.DateTimeField(auto_now=True)


    class Meta:
        ordering= ["-id"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

