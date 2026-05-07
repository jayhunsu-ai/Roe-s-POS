from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid



class StaffManager(BaseUserManager):
    def create_user(self, email, staffName, password=None, pin=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        if not staffName:
            raise ValueError('Staff name is required')
        if not password and pin:
            password = pin
        if not password:
            raise ValueError('Password is required')
        email = self.normalize_email(email)
        user = self.model(email=email, staffName=staffName, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, staffName, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', Staff.Roles.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, staffName, password, **extra_fields)



class Staff(AbstractUser):
    """
    Custom user model for staff members.
    Extends Django's built-in User to add POS-specific fields.
    """
    
    class Roles(models.TextChoices):
        ADMIN = 'Administrator', 'Administrator'
        CLERK = 'Clerk', 'Clerical staff'
        INVENTORY_MANAGER = 'InventoryManager', 'Inventory Manager'
        KITCHEN = 'Kitchen', 'Kitchen Staff'

    username = None
    first_name = None
    last_name = None

    staffId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staffName = models.CharField(max_length=250)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=25, choices=Roles.choices, default=Roles.CLERK)
    phone = models.CharField(max_length=20, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    lastLoginAt = models.DateTimeField(null=True, blank=True)
    failedPinAttempts = models.IntegerField(default=0)

    objects = StaffManager()
    
    # Use email as the unique identifier for login
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['staffName', 'role']
    
    class Meta:
        db_table = 'staff'
        verbose_name = 'Staff Member'
        verbose_name_plural = 'Staff'
    
    def __str__(self):
        return f"{self.staffName} ({self.get_role_display()})"


