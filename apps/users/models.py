from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator

class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Telefon raqami kiritilishi shart")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(phone_number, password, **extra_fields)

class CustomUser(AbstractUser):
    ADMIN = 'admin'
    SELLER = 'seller'
    BAKER = 'baker'
    MANAGER = 'manager'
    
    ROLE_CHOICES = [
        (ADMIN, 'Admin (Rahbar)'),
        (SELLER, 'Sotuvchi (Kassir)'),
        (BAKER, 'Nonvoy (Ishlab chiqaruvchi)'),
        (MANAGER, 'Omborchi / Menejer'),
    ]

    username = None
    phone_regex = RegexValidator(
        regex=r'^\+998\d{9}$', 
        message="Telefon raqami +998YYXXXXXXX ko'rinishida bo'lishi kerak."
    )
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=13, 
        unique=True, 
        verbose_name="Telefon raqami"
    )

    role = models.CharField(
        max_length=25, 
        choices=ROLE_CHOICES, 
        default=ADMIN,
        verbose_name="Roli"
    )

    full_name = models.CharField(max_length=255, verbose_name="F.I.SH")

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"