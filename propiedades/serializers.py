from rest_framework import serializers

from .models import Propiedad


class PropiedadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Propiedad
        fields = [
            "id",
            "external_id",
            "barrio",
            "rooms",
            "bedrooms",
            "bathrooms",
            "surface_total",
            "surface_covered",
            "price",
            "price_m2",
            "property_type",
            "amenity_garage",
            "amenity_pool",
            "amenity_security",
            "is_luminous",
            "near_transport",
            "is_a_estrenar",
            "is_reciclado",
        ]


class PrediccionRequestSerializer(serializers.Serializer):
    """Valida el payload de entrada para /api/predecir/."""

    barrio = serializers.CharField()
    surface_total = serializers.FloatField(min_value=1)
    rooms = serializers.FloatField(min_value=0)
    bathrooms = serializers.FloatField(min_value=0)
    amenity_garage = serializers.BooleanField(default=False)
    amenity_pool = serializers.BooleanField(default=False)
    amenity_security = serializers.BooleanField(default=False)
    is_luminous = serializers.BooleanField(default=False)
    near_transport = serializers.BooleanField(default=False)
    is_a_estrenar = serializers.BooleanField(default=False)
    is_reciclado = serializers.BooleanField(default=False)
