import re

from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("full_name", "phone", "city", "address", "notes")
        labels = {
            "full_name": "الاسم الكامل",
            "phone": "رقم الهاتف",
            "city": "المدينة",
            "address": "العنوان",
            "notes": "ملاحظات",
        }
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "input"}),
            "phone": forms.TextInput(
                attrs={"class": "input", "inputmode": "tel", "dir": "ltr"}
            ),
            "city": forms.TextInput(attrs={"class": "input"}),
            "address": forms.Textarea(attrs={"class": "textarea", "rows": 3}),
            "notes": forms.Textarea(attrs={"class": "textarea", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["address"].required = True

    def clean_full_name(self):
        value = " ".join(self.cleaned_data["full_name"].split())
        if len(value) < 3:
            raise forms.ValidationError("يرجى إدخال الاسم الكامل.")
        return value

    def clean_phone(self):
        value = self.cleaned_data["phone"].strip()
        if not re.fullmatch(r"[+\d\s().-]+", value) or len(re.sub(r"\D", "", value)) < 7:
            raise forms.ValidationError("يرجى إدخال رقم هاتف صالح.")
        return value

    def clean_city(self):
        value = self.cleaned_data["city"].strip()
        if len(value) < 2:
            raise forms.ValidationError("يرجى إدخال اسم المدينة.")
        return value

    def clean_address(self):
        value = self.cleaned_data["address"].strip()
        if len(value) < 5:
            raise forms.ValidationError("يرجى إدخال عنوان واضح.")
        return value
