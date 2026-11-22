"""
Django forms for user registration, login, profile updates, and delivery addresses.
Can be rendered directly in Developer 2's customer templates or validated via standard POST views.
Owned by Developer 1.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Address, CustomerProfile, RiderProfile, User
from .services import authenticate_user


class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=20, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email


class EmailOrUsernameLoginForm(forms.Form):
    identifier = forms.CharField(
        label="Username or Email",
        max_length=254,
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput,
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("identifier")
        password = cleaned_data.get("password")

        if identifier and password:
            self.user_cache = authenticate_user(self.request, identifier, password)
            if self.user_cache is None:
                raise forms.ValidationError("Invalid username/email or password.")
            if not self.user_cache.is_active:
                raise forms.ValidationError("This account is inactive.")
        return cleaned_data

    def get_user(self) -> User | None:
        return self.user_cache


class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email address is already in use.")
        return email


class CustomerNotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ("notify_email", "notify_sms")


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            "label",
            "line1",
            "line2",
            "city",
            "state",
            "postal_code",
            "country",
            "latitude",
            "longitude",
            "is_default",
        )


class RiderProfileForm(forms.ModelForm):
    class Meta:
        model = RiderProfile
        fields = (
            "vehicle_type",
            "plate_number",
            "is_available",
            "location_consent",
            "current_lat",
            "current_lng",
        )
