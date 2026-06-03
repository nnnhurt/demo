import csv
import os
from pathlib import Path
from typing import Any

from django.core.files import File
from django.core.management.color import no_style
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Model

from app.models import (
    Category,
    Punkt,
    Manufacturer,
    Zakaz,
    ZakazItem,
    Product,
    Supplier,
    Unit,
    User,
    ZakazStatus,
)

STATUS_FROM_CSV = {
    "новый": ZakazStatus.NEW,
    "завершен": ZakazStatus.DONE,
}


class Command(BaseCommand):
    @staticmethod
    def _find_import_photo(import_dir: Path, photo_name: str) -> Path | None:
        if not photo_name:
            return None

        src = import_dir / photo_name
        if not src.is_file():
            target = photo_name.lower()
            match = next(
                (p for p in import_dir.iterdir() if p.is_file() and p.name.lower() == target),
                None,
            )
            return match
        return src

    @staticmethod
    def _reset_pk_sequence(model: type[Model]) -> None:
        statements = connection.ops.sequence_reset_sql(no_style(), [model])
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)

    def handle(self, *args: Any, **options: Any) -> str | None:
        base_path = "import/"
        import_dir = Path(base_path)

        # pickup points (порядок строк = id в punkt_import / punkt_id в заказах)
        with open(os.path.join(base_path, "punkt_import.csv"), encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("address"):
                    continue
                Punkt.objects.get_or_create(adress=row["address"])

        # products and suppliers
        with open(os.path.join(base_path, "Tovar.csv"), encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row:
                    continue

                supplier, _ = Supplier.objects.get_or_create(name=row["supplier"])
                category, _ = Category.objects.get_or_create(name=row["category"])
                manufacturer, _ = Manufacturer.objects.get_or_create(
                    name=row["manufacturer"]
                )
                unit, _ = Unit.objects.get_or_create(name=row.get("unit", "шт."))

                photo_src = self._find_import_photo(
                    import_dir, row.get("photo", "").strip()
                )

                product, _ = Product.objects.update_or_create(
                    article=row["article"],
                    defaults={
                        "name": row["name"],
                        "unit": unit,
                        "price": row["price"],
                        "skidka": row.get("discount", 0),
                        "quantity": row["quantity"],
                        "description": row.get("description", ""),
                        "supplier": supplier,
                        "category": category,
                        "manufacturer": manufacturer,
                    },
                )
                if photo_src:
                    if product.photo:
                        product.photo.delete(save=False)
                    with photo_src.open("rb") as photo_file:
                        product.photo.save(photo_src.name, File(photo_file), save=True)

        # users (до заказов)
        with open(os.path.join(base_path, "user_import.csv"), encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row:
                    continue

                user, created = User.objects.get_or_create(
                    username=row["username"],
                    defaults={
                        "full_name": row["full_name"],
                        "role": row["role"],
                    },
                )
                if not created:
                    user.full_name = row["full_name"]
                    user.role = row["role"]
                    user.save(update_fields=["full_name", "role"])
                user.set_password(str(row["password"]).strip())
                user.save()

        # orders
        with open(os.path.join(base_path, "Заказ_import.csv"), encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row:
                    continue

                client_name = row["client_full_name"].strip()
                client = User.objects.filter(full_name=client_name).first()
                if client is None:
                    self.stderr.write(
                        f"Пропуск заказа {row['code']}: "
                        f"пользователь «{client_name}» не найден\n"
                    )
                    continue

                punkt_id = int(row["punkt_id"])
                pp_obj = (
                    Punkt.objects.filter(pk=punkt_id).first()
                    or Punkt.objects.first()
                )
                if pp_obj is None:
                    self.stderr.write(f"Пропуск заказа {row['code']}: нет пунктов выдачи\n")
                    continue

                status_key = row["status"].strip().lower()
                status = STATUS_FROM_CSV.get(status_key, ZakazStatus.NEW)

                order, _ = Zakaz.objects.update_or_create(
                    code=row["code"],
                    defaults={
                        "zakaz_date": row["order_date"],
                        "delivery_date": row["ship_date"] or None,
                        "client": client,
                        "status": status,
                        "punkt": pp_obj,
                    },
                )

                order.items.all().delete()
                items = [part.strip() for part in row["items"].split(",")]
                for i in range(0, len(items), 2):
                    if i + 1 >= len(items):
                        break
                    try:
                        prod = Product.objects.get(article=items[i])
                        ZakazItem.objects.create(
                            zakaz=order,
                            product=prod,
                            quantity=int(items[i + 1]),
                        )
                    except (Product.DoesNotExist, ValueError):
                        pass

        # корректный сброс последовательностей (тк id присутввуют в csv)
        self._reset_pk_sequence(Zakaz)
        self._reset_pk_sequence(ZakazItem)
        self.stdout.write(self.style.SUCCESS("Импорт завершён"))
