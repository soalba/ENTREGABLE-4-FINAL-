from django.db import models


class Propiedad(models.Model):
    """
    Representa una unidad (departamento) en venta en CABA.
    Replica las columnas relevantes de entrenamiento_limpio_CORREGIDO.csv
    usadas por el modelo de Machine Learning (Entregable 3).
    """

    # Identificador original del dataset (no PK de Django, puede repetirse en cargas manuales)
    external_id = models.BigIntegerField(null=True, blank=True, db_index=True)

    barrio = models.CharField(max_length=100, db_index=True)  # columna l3 del dataset

    rooms = models.FloatField(null=True, blank=True)        # ambientes
    bedrooms = models.FloatField(null=True, blank=True)     # dormitorios
    bathrooms = models.FloatField(null=True, blank=True)    # baños

    surface_total = models.FloatField(null=True, blank=True)
    surface_covered = models.FloatField(null=True, blank=True)

    price = models.FloatField(null=True, blank=True)        # precio total USD
    price_m2 = models.FloatField(null=True, blank=True)     # precio por m2 USD

    property_type = models.CharField(max_length=50, default="Departamento")

    amenity_garage = models.BooleanField(default=False)
    amenity_pool = models.BooleanField(default=False)
    amenity_security = models.BooleanField(default=False)
    is_luminous = models.BooleanField(default=False)
    near_transport = models.BooleanField(default=False)
    is_a_estrenar = models.BooleanField(default=False)
    is_reciclado = models.BooleanField(default=False)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["barrio"]),
            models.Index(fields=["price"]),
            models.Index(fields=["rooms"]),
        ]

    def __str__(self):
        return f"{self.property_type} en {self.barrio} - USD {self.price}"
