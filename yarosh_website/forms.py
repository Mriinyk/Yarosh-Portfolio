from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UsernameField
from django.core.exceptions import ValidationError

from .models import ContactRequest, PhotoSession, PhotoSessionType


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


class PhotoSessionForm(forms.ModelForm):
    photo_type = forms.ChoiceField(
        choices=(),
        required=False,
        label="Тип фотосесії",
    )
    new_category = forms.CharField(
        max_length=100,
        required=False,
        label="Нова категорія",
        widget=forms.TextInput(
            attrs={
                "class": "form-control photo-form-control",
                "placeholder": "Введіть назву нової категорії",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = PhotoSession
        fields = (
            "title",
            "photo_type",
            "cover_url",
            "drive_folder_url",
        )
        labels = {
            "title": "Назва фотосесії",
            "cover_url": "Посилання на обкладинку",
            "drive_folder_url": "Посилання на папку Google Drive",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control photo-form-control",
                    "placeholder": "Введіть назву фотосесії",
                }
            ),
            "cover_url": forms.URLInput(
                attrs={
                    "class": "form-control photo-form-control",
                    "placeholder": "Посилання на обкладинку",
                }
            ),
            "drive_folder_url": forms.URLInput(
                attrs={
                    "class": "form-control photo-form-control",
                    "placeholder": "Посилання на папку Google Drive",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo_type"].choices = [
            ("", "Без категорії"),
            *PhotoSessionType.objects.values_list("pk", "name"),
            ("__new__", "Додати нову категорію"),
        ]
        self.fields["photo_type"].widget.attrs["class"] = (
            "form-select photo-form-control"
        )
        if self.instance.pk:
            self.initial["photo_type"] = (
                str(self.instance.photo_type_id)
                if self.instance.photo_type_id
                else ""
            )

    def clean(self):
        cleaned_data = super().clean()
        selected_type = cleaned_data.get("photo_type")
        new_category = (cleaned_data.get("new_category") or "").strip()
        if selected_type == "__new__":
            if not new_category:
                self.add_error(
                    "new_category",
                    ValidationError(
                        "Вкажіть назву нової категорії.",
                        code="required",
                    ),
                )
                cleaned_data["photo_type"] = None
            else:
                cleaned_data["photo_type"] = None
        elif selected_type:
            cleaned_data["photo_type"] = PhotoSessionType.objects.get(
                pk=selected_type
            )
        else:
            cleaned_data["photo_type"] = None
        cleaned_data["new_category"] = new_category
        return cleaned_data

    def save(self, commit=True):
        photo_session = super().save(commit=False)
        new_category = self.cleaned_data.get("new_category")
        if new_category:
            photo_session.photo_type, _ = PhotoSessionType.objects.get_or_create(
                name=new_category,
            )
        photo_session.is_active = True
        if commit:
            photo_session.save()
            self.save_m2m()
        return photo_session
