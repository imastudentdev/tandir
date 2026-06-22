from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, 
        label="Parol",
        help_text="Foydalanuvchi uchun parol kiriting."
    )

    class Meta:
        model = CustomUser
        fields = ('phone_number', 'full_name', 'role', 'password')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = '__all__'


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    
    list_display = ('phone_number', 'full_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_active')
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Shaxsiy ma\'lumotlar', {'fields': ('full_name', 'role')}),
        ('Huquqlar', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'full_name', 'role', 'password'),
        }),
    )
    ordering = ('phone_number',)
