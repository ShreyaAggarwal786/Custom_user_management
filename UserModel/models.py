
from django.contrib.auth.models import AbstractUser
from django.db import models

from django.conf import settings


class User(AbstractUser):    
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

    profile= models.ForeignKey(
        'Profile',
        on_delete= models.SET_NULL,
        related_name= "users",
        blank=True, null=True
    )

    username= models.CharField(max_length=100, unique= True, blank=True, null=True)
    email= models.EmailField(unique= True, blank=True, null=True)
    
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
    status= models.CharField(max_length=10, choices=Status.choices, default= Status.ACTIVE, blank= True, null=True)
    
    otp_code= models.CharField(max_length=6, blank=True,  null=True)
    otp_purpose=models.CharField(max_length=20,blank=True, null=True)
    otp_expires_at= models.DateTimeField(null=True, blank=True)
    otp_attempts= models.PositiveSmallIntegerField(default=0)

    otp_request_count= models.PositiveSmallIntegerField(default=0)
    otp_window_start= models.DateTimeField(null= True, blank=True)
    otp_blocked_until= models.DateTimeField(null=True, blank=True)


    # def save(self, *args, **kwargs):
    #     if self.profiles:
    #         self.profiles= self.profiles.strip().lower()
    #     if not self.profiles:
    #         self.profiles = "standard"
    #     super().save(*args, **kwargs)

    def __str__(self):
        return self.email or f"User.{self.pk}"

class Profile(models.Model):
        role= models.CharField(max_length=50, unique=True,blank=True, null=True)
        is_default= models.BooleanField(default=False)

        class Meta:
            ordering=['-id']

        def __str__(self):
            return self.role or f"Profile.{self.pk}"


#client model
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
        'User',
        on_delete= models.PROTECT,
        related_name="clients_created"
    )
    created_at=models.DateTimeField(auto_now_add=True)


    modified_by= models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name="clients_modified"
    ) 
    modified_at=models.DateTimeField(auto_now=True)


    class Meta:
        ordering= ["-id"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"



#project model
class Project(models.Model):
    Project_Status=[
        ('Active','Active'),
        ('Completed','Completed'),
        ('Inprogress','Inprogress'),
        ('Pending','Pending'),
        ('Inactive','Inactive'),
    ]

    project_title= models.CharField(max_length=100, blank=True, null= True)
    project_type=  models.CharField(max_length=100,  blank=True, null= True)
    description= models.TextField(blank=True, null=True)
    project_status=  models.CharField(max_length=100, choices=Project_Status, default= 'Inprogress', blank=True, null= True)
    date_of_completion= models.DateField(blank=True, null= True)

    client= models.ForeignKey(
        'Client',
        on_delete= models.PROTECT,
        related_name="projects",
        null=True, blank=True
    )
    manager= models.ForeignKey(
        'User',
        on_delete= models.PROTECT,
        related_name= "managed_projects",
        null= True, blank=True
    )
    created_by= models.ForeignKey(
        'User',
        on_delete= models.PROTECT,
        related_name= 'created_projects',
        null=True,blank=True
    )
    created_at= models.DateTimeField(auto_now_add=True,null=True,blank=True)
    
    modified_by= models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='modified_projects',
        null=True,blank=True
    )
    modified_at= models.DateTimeField(auto_now=True,null=True,blank=True)

    # @property
    # def total_attachement(self):
    #     return self.projectattachement_set.count()

    # @property
    # def attachement_list(self):
    #     return list(self.projectattachement_set.values('id','file_name'))

    
    def __str__(self):
        return self.project_title or f" Project.{self.pk}"

class ProjectAttachement(models.Model):
    project= models.ForeignKey(
        'Project',
        on_delete= models.PROTECT,
        blank=True, null=True
    )

    file= models.FileField(upload_to="project_attachements/%y%m", null= True, blank=True)
    file_name= models.CharField(max_length=255,blank= True, null=True)
    # file_size= models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.file_name or f"Attachement.{self.pk}"




