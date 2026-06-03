import uuid
from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


def product_photo_upload_to(instance: "Product", filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".jpg"
    if instance.pk:
        return f"product/{instance.pk}{ext}"
    return f"product/{uuid.uuid4().hex}{ext}"


class User(AbstractUser):
    role = models.CharField(_("Роль"), max_length=300)
    full_name = models.CharField(_("ФИО"), max_length=100)

    def __str__(self) -> str:
        return self.full_name


class Category(models.Model):
    name = models.CharField(_("Название"))

    class Meta:
        verbose_name = _("Категория")
        verbose_name_plural = _("Категории")

    def __str__(self) -> str:
        return self.name


class Manufacturer(models.Model):
    name = models.CharField(_("Название"))

    class Meta:
        verbose_name = _("Производитель")
        verbose_name_plural = _("Производители")

    def __str__(self) -> str:
        return self.name


class Supplier(models.Model):
    name = models.CharField(_("Название"))

    class Meta:
        verbose_name = _("Поставщик")
        verbose_name_plural = _("Поставщики")

    def __str__(self) -> str:
        return self.name


class Unit(models.Model):
    name = models.CharField(_("Название"))

    class Meta:
        verbose_name = _("Единица измерения")
        verbose_name_plural = _("Единицы измерения")

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    article = models.CharField(_("Артикул"), unique=True)
    name = models.CharField(_("Наименование"))
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        verbose_name=_("Единица измерения"),
    )
    price = models.DecimalField(
        _("Цена"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.PROTECT,
        verbose_name=_("Производитель"),
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        verbose_name=_("Поставщик"),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        verbose_name=_("Категория"),
    )
    quantity = models.PositiveIntegerField(_("Количество на складе"))
    description = models.CharField(_("Описание"))
    skidka = models.IntegerField(
        _("Скидка, %"),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    photo = models.ImageField(
        _("Фото"),
        upload_to=product_photo_upload_to,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Товар")
        verbose_name_plural = _("Товары")

    def save(self, *args, **kwargs):
        if self.photo is False:
            self.photo = None

        pending_photo: UploadedFile | None = None
        if isinstance(self.photo, UploadedFile):
            pending_photo = self.photo
            self.photo = None

        if self.pk:
            try:
                old = Product.objects.get(pk=self.pk)
                if old.photo and (pending_photo is not None or not self.photo):
                    old.photo.delete(save=False)
            except Product.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if pending_photo is not None:
            ext = Path(pending_photo.name).suffix.lower() or ".jpg"
            self.photo.save(f"upload{ext}", pending_photo, save=True)

    @property
    def final_price(self):
        if self.skidka:
            return self.price * (100 - self.skidka) / 100
        return self.price

    def __str__(self) -> str:
        return f"{self.article} — {self.name}"


class Punkt(models.Model):
    adress = models.CharField(_("Адрес"))

    class Meta:
        verbose_name = _("Пункт выдачи")
        verbose_name_plural = _("Пункты выдачи")

    def __str__(self) -> str:
        return self.adress


class ZakazStatus(models.TextChoices):
    NEW = "new", _("Новый")
    DONE = "done", _("Завершён")


class Zakaz(models.Model):
    code = models.CharField(_("Код заказа"), max_length=32, unique=True)
    status = models.CharField(
        _("Статус"),
        max_length=32,
        choices=ZakazStatus.choices,
        default=ZakazStatus.NEW,
    )
    zakaz_date = models.DateField(_("Дата заказа"))
    delivery_date = models.DateField(_("Дата доставки"), blank=True, null=True)
    punkt = models.ForeignKey(
        Punkt,
        on_delete=models.PROTECT,
        related_name="zakazs",
        verbose_name=_("Пункт выдачи"),
    )
    client = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="zakazy",
        verbose_name=_("Клиент"),
    )

    class Meta:
        verbose_name = _("Заказ")
        verbose_name_plural = _("Заказы")

    def __str__(self) -> str:
        return self.code


class ZakazItem(models.Model):
    zakaz = models.ForeignKey(
        Zakaz,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Заказ"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="zakaz_items",
        verbose_name=_("Товар"),
    )
    quantity = models.PositiveIntegerField(
        _("Количество"),
        default=1,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = _("Позиция заказа")
        verbose_name_plural = _("Позиции заказа")
