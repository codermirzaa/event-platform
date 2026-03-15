from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser


class RegisterForm(UserCreationForm):
    """Registration form — user chooses Attendee or Organizer role."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
        })
    )

    role = forms.ChoiceField(
        choices=[
            (CustomUser.Role.ATTENDEE, 'Attendee — I want to discover & book events'),
            (CustomUser.Role.ORGANIZER, 'Organizer — I want to create & manage events'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial=CustomUser.Role.ATTENDEE,
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        bootstrap_fields = ['username', 'first_name', 'last_name', 'password1', 'password2']
        placeholders = {
            'username': 'Username',
            'first_name': 'First name',
            'last_name': 'Last name',
            'password1': 'Password',
            'password2': 'Confirm password',
        }
        for field in bootstrap_fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': placeholders.get(field, ''),
            })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Login form with Bootstrap styling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username',
            'autofocus': True,
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password',
        })


class ProfileUpdateForm(forms.ModelForm):
    """Form to update user profile info."""

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone', 'bio')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+994 xx xxx xx xx'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
