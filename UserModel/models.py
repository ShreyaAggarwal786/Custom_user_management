
from django.contrib.auth.models import AbstractUser
from django.db import models

from django.conf import settings



class User(AbstractUser):
    class Profile(models.TextChoices):
        ADMINISTRATOR= "administrator", "Administrator"
        STANDARD= "standard", "Standard"
        DEVELOPER= "developer", "Developer"
        CLIENT= "client", "Client"
        HUMAN_RESOURCES= "human_resources", "Human_Resources"

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

    username= models.CharField(max_length=100, unique= True, blank=True, null=True)
    email= models.EmailField(unique= True, blank=True, null=True)
    profiles= models.CharField(max_length= 20, choices=Profile.choices, default= Profile.STANDARD)
    date_of_birth= models.DateField(blank=True, null=True )
    gender= models.CharField(max_length=10, choices=Gender.choices, blank= True, null=True)
    nationality= models.CharField(max_length= 70, blank=True, null=True)
    image= models.ImageField(upload_to= "Profile_images/", null= True, blank=True)
    blood_group= models.CharField(max_length=3, choices=Blood_Group.choices, blank=True, null=True)
    phone= models.CharField(max_length=15,blank= True, null=True)
    permanent_address= models.TextField( blank=True,  null=True)
    current_address=models.TextField( blank=True,  null=True)
    emergency_contact_name= models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_number= models.CharField(max_length=15, blank= True,  null=True)
    emergency_contact_relationship= models.CharField(max_length= 50, blank=True,  null=True)
    status= models.CharField(max_length=10, choices=Status.choices, default= Status.ACTIVE)
    
    otp_code= models.CharField(max_length=6, blank=True,  null=True)
    otp_purpose=models.CharField(max_length=20,blank=True, null=True)
    otp_expires_at= models.DateTimeField(null=True, blank=True)
    otp_attempts= models.PositiveSmallIntegerField(default=0)

    verify_request_count= models.PositiveSmallIntegerField(default=0)
    verify_window_start= models.DateTimeField(null= True, blank=True)
    verify_blocked_until= models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email or self.username or f"User.{self.pk}"



class Client(models.Model):
    class Status(models.TextChoices):
        ACTIVE="active","Active"
        INACTIVE="inactive","Inactive"


    first_name= models.CharField(max_length=100,blank=True, null=True)
    last_name= models.CharField(max_length=100, blank=True, null=True)
    email= models.EmailField(max_length=254, unique=True)
    contact_number=models.CharField(max_length=15, blank=True, null=True)
    address=models.TextField(blank=True, null=True)
    country= models.CharField(max_length=100, blank=True, null=True)
    status= models.CharField(max_length=10, choices= Status.choices, default=Status.ACTIVE)

    created_by= models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete= models.PROTECT,
        related_name="clients_created"
    )
    created_at=models.DateTimeField(auto_now_add=True)


    modified_by= models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clients_modified"
    ) 
    modified_at=models.DateTimeField(auto_now=True)


    class Meta:
        ordering= ["-id"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

