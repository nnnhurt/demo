from django import forms
from django.utils.translation import gettext_lazy as _
from extra_views import InlineFormSetFactory

from app.models import User, Zakaz, ZakazItem, Product

DATE_INPUT = forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "photo",
            "article",
            "name",
            "category",
            "description",
            "manufacturer",
            "supplier",
            "price",
            "unit",
            "quantity",
            "skidka",
        ]
        widgets = {
            "photo": forms.ClearableFileInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo"].widget.clear_checkbox_label = _("Удалить фото")
        self.fields["photo"].required = False


class ZakazForm(forms.ModelForm):
    class Meta:
        model = Zakaz
        fields = [
            "code",
            "status",
            "punkt",
            "zakaz_date",
            "delivery_date",
            "client",
        ]
        widgets = {
            "zakaz_date": DATE_INPUT,
            "delivery_date": DATE_INPUT,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = User.objects.order_by("full_name")
        for name in ("zakaz_date", "delivery_date"):
            self.fields[name].input_formats = ["%Y-%m-%d"]


class ZakazItemInline(InlineFormSetFactory):
    model = ZakazItem
    fields = ["product", "quantity"]
    extra = 5
    can_delete = True
