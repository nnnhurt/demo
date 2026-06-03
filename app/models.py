import secrets
import string
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from PIL import Image


def _photo_random_suffix(length: int = 6) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def product_photo_upload_to(instance: "Product", filename: str) -> str:
    path = Path(filename)
    ext = path.suffix.lower() or ".jpg"
    name = path.stem.lower()
    return f"product/{name}_{_photo_random_suffix()}{ext}"


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

    def _resize_photo(self) -> None:
        if not self.photo:
            return
        path = Path(self.photo.path)
        if not path.is_file():
            return
        with Image.open(path) as img:
            img.thumbnail(settings.PRODUCT_PHOTO_SIZE, Image.Resampling.LANCZOS)
            img.save(path)

    def save(self, *args, **kwargs) -> None:
        if self.photo is False:
            self.photo = None

        pending = self.photo if isinstance(self.photo, UploadedFile) else None
        if pending:
            self.photo = None

        if self.pk:
            try:
                old = Product.objects.get(pk=self.pk)
                if old.photo and (pending or not self.photo):
                    old.photo.delete(save=False)
            except Product.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if pending:
            self.photo.save(pending.name, pending, save=False)
            self._resize_photo()
            Product.objects.filter(pk=self.pk).update(photo=self.photo.name)

    def delete(self, *args, **kwargs) -> None:
        if self.photo:
            self.photo.delete(save=False)
        super().delete(*args, **kwargs)

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
