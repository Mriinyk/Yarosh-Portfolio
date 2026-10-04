from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UsernameField

from .models import ContactRequest


class SiteAuthenticationForm(AuthenticationForm):
    username = UsernameField(
        label="Ім'я користувача",
        widget=forms.TextInput(
            attrs={
                "autocapitalize": "none",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class SiteUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.pop("autofocus", None)
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactRequest
        fields = ["contact_method", "social_username", "message"]
        widgets = {
            "contact_method": forms.RadioSelect,
            "social_username": forms.TextInput(
                attrs={"placeholder": "@nickname", "autocomplete": "username"}
            ),
            "message": forms.Textarea(
                attrs={"placeholder": "Ваше повідомлення", "rows": 4}
            ),
        }
        labels = {
            "contact_method": "Оберіть соціальну мережу для зв'язку",
            "social_username": "Введіть нік Telegram",
            "message": "Напишіть повідомлення",
        }
