"""
Comando de gestión: carga el dataset de propiedades a la base SQLite.

Uso:
    python manage.py import_csv                          # usa la ruta por defecto
    python manage.py import_csv --path otro_archivo.csv
    python manage.py import_csv --reset                  # borra los datos existentes antes de cargar
"""
import math
import os

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

from propiedades.models import Propiedad

DEFAULT_CSV_PATH = os.path.join(settings.BASE_DIR, "dataset_listo.csv")

BOOL_COLS = [
    "amenity_garage", "amenity_pool", "amenity_security",
    "is_luminous", "near_transport", "is_a_estrenar", "is_reciclado",
]


def _f(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


class Command(BaseCommand):
    help = "Importa el dataset de propiedades (CSV) a la base de datos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path", type=str, default=DEFAULT_CSV_PATH,
            help="Ruta al CSV a importar (default: backend/dataset_listo.csv)",
        )
        parser.add_argument(
            "--reset", action="store_true",
            help="Borra todas las propiedades existentes antes de importar.",
        )
        parser.add_argument(
            "--batch-size", type=int, default=2000,
            help="Tamaño de lote para bulk_create (default: 2000).",
        )

    def handle(self, *args, **options):
        path = options["path"]
        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f"No se encontró el archivo: {path}"))
            return

        if options["reset"]:
            borradas, _ = Propiedad.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Se borraron {borradas} propiedades existentes."))

        self.stdout.write(f"Leyendo {path} ...")
        df = pd.read_csv(path)

        # Compatibilidad: aceptar tanto dataset_listo.csv (columna 'barrio')
        # como el CSV original del Entregable 2/3 (columna 'l3' + operation_type)
        if "barrio" not in df.columns and "l3" in df.columns:
            df = df.rename(columns={"l3": "barrio"})
        if "operation_type" in df.columns:
            df = df[df["operation_type"] == "venta"].copy()

        for c in BOOL_COLS:
            if c in df.columns:
                df[c] = df[c].fillna(False).astype(bool)
            else:
                df[c] = False

        total = len(df)
        self.stdout.write(f"Importando {total:,} filas...")

        batch_size = options["batch_size"]
        objetos = []
        creadas = 0
        omitidas = 0

        for idx, row in df.iterrows():
            barrio = str(row.get("barrio", "")).strip()
            if not barrio or barrio.lower() == "nan":
                omitidas += 1
                continue

            objetos.append(Propiedad(
                external_id=_f(row.get("id")),
                barrio=barrio,
                rooms=_f(row.get("rooms")),
                bedrooms=_f(row.get("bedrooms")),
                bathrooms=_f(row.get("bathrooms")),
                surface_total=_f(row.get("surface_total")),
                surface_covered=_f(row.get("surface_covered")),
                price=_f(row.get("price")),
                price_m2=_f(row.get("price_m2")),
                property_type=row.get("property_type") or "Departamento",
                amenity_garage=bool(row.get("amenity_garage")),
                amenity_pool=bool(row.get("amenity_pool")),
                amenity_security=bool(row.get("amenity_security")),
                is_luminous=bool(row.get("is_luminous")),
                near_transport=bool(row.get("near_transport")),
                is_a_estrenar=bool(row.get("is_a_estrenar")),
                is_reciclado=bool(row.get("is_reciclado")),
            ))
            creadas += 1

            if len(objetos) >= batch_size:
                Propiedad.objects.bulk_create(objetos)
                self.stdout.write(f"  ... {creadas:,}/{total:,} procesadas")
                objetos = []

        if objetos:
            Propiedad.objects.bulk_create(objetos)

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Importación finalizada: {creadas:,} propiedades cargadas, {omitidas} filas omitidas (sin barrio)."
        ))
