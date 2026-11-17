
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class BaseModel(models.Model):
    created_by= models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete= models.SET_NULL,
        related_name="%(class)s_created",
        null=True, blank=True
    )
    created_at= models.DateTimeField(auto_now_add=True,blank=True,null=True)
    modified_by= models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete= models.SET_NULL,
        related_name= "%(class)s_modified",
        null=True,blank=True
    )
    modified_at= models.DateTimeField(auto_now=True,blank=True,null=True)

    class Meta:
        abstract=True

class User(AbstractUser, BaseModel):    
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
    
    otp_code= models.JSONField(default=dict, blank=True,  null=True)
    otp_request_timestamps= models.JSONField(default=list, blank=True, null=True)

    # created_by= models.ForeignKey('self',on_delete= models.SET_NULL,related_name='users_created',null=True, blank=True)
    # created_at= models.DateTimeField(auto_now_add=True, blank=True,null=True)
    # modified_by=models.ForeignKey('self',on_delete= models.SET_NULL,related_name='users_modified',null=True, blank=True)
    # modified_at= models.DateTimeField(auto_now=True, blank=True,null=True)

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
class Client(BaseModel):
    class Status(models.TextChoices):
        ACTIVE="active","Active"
        INACTIVE="inactive","Inactive"


    first_name= models.CharField(max_length=100,blank=True, null=True)
    last_name= models.CharField(max_length=100, blank=True, null=True)
    email= models.EmailField(max_length=254, unique=True,blank=True, null=True)
    contact_number=models.CharField(max_length=15, blank=True, null=True)
    address=models.TextField(blank=True, null=True)
    country= models.CharField(max_length=100, blank=True, null=True)
    status= models.CharField(max_length=10, choices= Status.choices, default=Status.ACTIVE,blank=True, null=True)

    # created_by= models.ForeignKey('User',on_delete= models.PROTECT,related_name="clients_created",null=True, blank=True)
    # created_at=models.DateTimeField(auto_now_add=True,null=True, blank=True)
    # modified_by= models.ForeignKey('User',on_delete=models.PROTECT,related_name="clients_modified",blank=True, null=True) 
    # modified_at=models.DateTimeField(auto_now=True, blank=True, null=True)


    class Meta:
        ordering= ["-id"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"



#project model
class Project(BaseModel):
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
    start_date= models.DateField(auto_now_add=True, blank=True, null=True)
    date_of_completion= models.DateField(blank=True, null= True)
    is_deleted= models.BooleanField(default=False)

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
    # created_by= models.ForeignKey('User',on_delete= models.PROTECT,related_name= 'created_projects',null=True, blank=True)
    # created_at= models.DateTimeField(auto_now_add=True,null=True,blank=True)   
    # modified_by= models.ForeignKey( 'User',on_delete=models.PROTECT,related_name='modified_projects',null=True, blank=True)
    # modified_at= models.DateTimeField(auto_now=True,null=True,blank=True)
        
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

# Project Task Model
class ProjectTask(BaseModel):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Inprogress', 'Inprogress'),
        ('Completed', 'Completed'),
        ('On Hold', 'On Hold'),
        ('Cancelled', 'Cancelled'),
    ]

    project = models.ForeignKey('Project',on_delete=models.PROTECT,related_name='tasks',null=True,blank=True)
    assign_by = models.ForeignKey('User',on_delete=models.PROTECT,related_name='assigned_by_tasks',null=True,blank=True)
    assign_to = models.ForeignKey('User',on_delete=models.PROTECT,related_name='assigned_tasks',null=True,blank=True)
    title = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    task_status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='Pending',null=True,blank=True)
    is_deleted = models.BooleanField(default=False)
    task_start_date = models.DateField(auto_now_add=True,null=True,blank=True)
    task_complete_date = models.DateField(null=True, blank=True)
    # created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    # created_by = models.ForeignKey('User',on_delete=models.PROTECT,related_name='created_tasks',null=True,blank=True)
    # updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    # updated_by = models.ForeignKey('User',on_delete=models.PROTECT,related_name='updated_tasks',null=True,blank=True)

    class Meta:
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'title'],
                name='unique_task_title_per_project'
            )]

    def __str__(self):
        return self.title or f"Task.{self.pk}"


class TaskComment(models.Model):
    task = models.ForeignKey('ProjectTask',on_delete=models.CASCADE,related_name='comments', blank= True, null=True)
    user = models.ForeignKey('User',on_delete=models.PROTECT,related_name='task_comments', blank= True, null=True)
    comment = models.TextField(blank= True, null=True)
    class Meta:
        ordering=['-id']
    def __str__(self):
        return f"Comment on Task {self.task_id} by {self.user_id}"
