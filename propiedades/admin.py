from django.contrib import admin

from .models import Propiedad


@admin.register(Propiedad)
class PropiedadAdmin(admin.ModelAdmin):
    list_display = (
        "id", "barrio", "rooms", "bathrooms", "surface_total",
        "price", "price_m2", "amenity_garage", "amenity_pool", "amenity_security",
    )
    list_filter = ("barrio", "amenity_garage", "amenity_pool", "amenity_security", "is_a_estrenar")
    search_fields = ("barrio", "external_id")
    list_per_page = 50
