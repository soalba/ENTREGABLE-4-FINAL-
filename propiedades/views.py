import io
import logging

import numpy as np
import pandas as pd
from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .ml import get_barrios_validos, get_metadata, get_pipeline
from .models import Propiedad
from .serializers import PrediccionRequestSerializer, PropiedadSerializer

logger = logging.getLogger(__name__)

NUM_FEATURES = [
    "surface_total", "rooms", "bathrooms",
    "amenity_garage", "amenity_pool", "amenity_security",
    "is_luminous", "near_transport", "is_a_estrenar", "is_reciclado",
]


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in ("true", "1", "1.0", "yes", "si", "sí", "t")


def _safe_float(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


class PropiedadPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 200


@api_view(["GET"])
def listar_propiedades(request):
    """
    GET /api/propiedades/

    Filtros combinables vía query params:
      - barrio (repetible: ?barrio=Palermo&barrio=Almagro)
      - precio_min, precio_max (sobre price, USD)
      - ambientes_min, ambientes_max (rooms)
      - banios_min (bathrooms)
      - superficie_min, superficie_max (surface_total)
      - garage, pileta, seguridad, luminoso, cerca_transporte, a_estrenar, reciclado (true/false)
      - ordenar: campo de ordenamiento, ej. "price", "-price", "surface_total"
      - page, page_size: paginación
    """
    qs = Propiedad.objects.all()

    barrios = [b for b in request.GET.getlist("barrio") if b]
    if barrios:
        qs = qs.filter(barrio__in=barrios)

    def _filter_range(qs, param_min, param_max, field):
        v_min = request.GET.get(param_min)
        v_max = request.GET.get(param_max)
        if v_min not in (None, ""):
            try:
                qs = qs.filter(**{f"{field}__gte": float(v_min)})
            except ValueError:
                pass
        if v_max not in (None, ""):
            try:
                qs = qs.filter(**{f"{field}__lte": float(v_max)})
            except ValueError:
                pass
        return qs

    qs = _filter_range(qs, "precio_min", "precio_max", "price")
    qs = _filter_range(qs, "ambientes_min", "ambientes_max", "rooms")
    qs = _filter_range(qs, "superficie_min", "superficie_max", "surface_total")

    banios_min = request.GET.get("banios_min")
    if banios_min not in (None, ""):
        try:
            qs = qs.filter(bathrooms__gte=float(banios_min))
        except ValueError:
            pass

    amenity_param_map = {
        "garage": "amenity_garage",
        "pileta": "amenity_pool",
        "seguridad": "amenity_security",
        "luminoso": "is_luminous",
        "cerca_transporte": "near_transport",
        "a_estrenar": "is_a_estrenar",
        "reciclado": "is_reciclado",
    }
    for param, field in amenity_param_map.items():
        val = request.GET.get(param)
        if val is not None and val.lower() in ("true", "1"):
            qs = qs.filter(**{field: True})

    ordenar = request.GET.get("ordenar")
    campos_validos = {
        "price", "-price", "price_m2", "-price_m2",
        "surface_total", "-surface_total", "rooms", "-rooms", "id", "-id",
    }
    if ordenar in campos_validos:
        qs = qs.order_by(ordenar)

    paginator = PropiedadPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = PropiedadSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
def listar_barrios(request):
    """GET /api/barrios/ — barrios disponibles en la base, con cantidad de propiedades."""
    data = (
        Propiedad.objects.values("barrio")
        .annotate(cantidad=Count("id"))
        .order_by("-cantidad")
    )
    data = [d for d in data if d["barrio"]]
    return Response(data)


@api_view(["GET"])
def estadisticas(request):
    """
    GET /api/estadisticas/

    Datos agregados para alimentar los gráficos del frontend (equivalentes a
    los del Entregable 3): precio mediano por barrio, distribución de
    price_m2 e importancia agregada de variables del modelo.
    """
    qs = Propiedad.objects.exclude(price_m2__isnull=True)
    valores = list(qs.values("barrio", "price_m2", "price", "surface_total"))
    if not valores:
        return Response({
            "precio_m2_por_barrio": [],
            "distribucion_price_m2": [],
            "resumen_global": {},
            "importancia_variables": [],
        })

    df = pd.DataFrame(valores)
    df = df.dropna(subset=["barrio", "price_m2"])

    agg = (
        df.groupby("barrio")["price_m2"]
        .agg(mediana="median", cantidad="count")
        .reset_index()
        .sort_values("mediana", ascending=False)
    )
    agg = agg[agg["cantidad"] >= 5]
    precio_m2_por_barrio = [
        {"barrio": row.barrio, "mediana_usd_m2": round(row.mediana, 1), "cantidad": int(row.cantidad)}
        for row in agg.itertuples()
    ]

    q99 = df["price_m2"].quantile(0.99)
    serie = df[df["price_m2"] < q99]["price_m2"]
    counts, bin_edges = np.histogram(serie, bins=30)
    distribucion = [
        {
            "rango_min": round(float(bin_edges[i]), 0),
            "rango_max": round(float(bin_edges[i + 1]), 0),
            "frecuencia": int(counts[i]),
        }
        for i in range(len(counts))
    ]

    resumen_global = {
        "total_propiedades": int(len(df)),
        "mediana_price_m2": round(float(df["price_m2"].median()), 1),
        "promedio_price_m2": round(float(df["price_m2"].mean()), 1),
        "barrios_distintos": int(df["barrio"].nunique()),
    }

    importancia_variables = []
    try:
        pipeline = get_pipeline()
        modelo = pipeline.named_steps["model"]
        preproc = pipeline.named_steps["preprocessor"]
        ohe = preproc.named_transformers_["cat"]
        barrios_ohe = ohe.get_feature_names_out(["l3"]).tolist()
        feature_names = NUM_FEATURES + barrios_ohe
        importancias = modelo.feature_importances_

        imp_barrio = sum(v for n, v in zip(feature_names, importancias) if n.startswith("l3_"))
        imp_otras = {
            n: float(v) for n, v in zip(feature_names, importancias) if not n.startswith("l3_")
        }
        importancia_variables = [{"variable": "barrio", "importancia": round(float(imp_barrio), 4)}]
        importancia_variables += [
            {"variable": n, "importancia": round(v, 4)}
            for n, v in sorted(imp_otras.items(), key=lambda x: -x[1])
        ]
    except Exception as e:
        logger.warning("No se pudo calcular importancia de variables: %s", e)

    return Response({
        "precio_m2_por_barrio": precio_m2_por_barrio,
        "distribucion_price_m2": distribucion,
        "resumen_global": resumen_global,
        "importancia_variables": importancia_variables,
    })


@api_view(["POST"])
def predecir_precio(request):
    """
    POST /api/predecir/
    Recibe las características de una propiedad y devuelve el precio
    estimado por m² y total, usando el pipeline Gradient Boosting entrenado
    en el Entregable 3.
    """
    serializer = PrediccionRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    datos = serializer.validated_data

    barrios_validos = get_barrios_validos()
    if barrios_validos and datos["barrio"] not in barrios_validos:
        return Response(
            {"error": f"Barrio '{datos['barrio']}' no reconocido por el modelo.",
             "barrios_validos": barrios_validos},
            status=status.HTTP_400_BAD_REQUEST,
        )

    fila = pd.DataFrame([{
        "surface_total": datos["surface_total"],
        "rooms": datos["rooms"],
        "bathrooms": datos["bathrooms"],
        "amenity_garage": int(datos["amenity_garage"]),
        "amenity_pool": int(datos["amenity_pool"]),
        "amenity_security": int(datos["amenity_security"]),
        "is_luminous": int(datos["is_luminous"]),
        "near_transport": int(datos["near_transport"]),
        "is_a_estrenar": int(datos["is_a_estrenar"]),
        "is_reciclado": int(datos["is_reciclado"]),
        "l3": datos["barrio"],
    }])

    try:
        pipeline = get_pipeline()
        pred_m2 = float(pipeline.predict(fila)[0])
    except (FileNotFoundError, RuntimeError) as e:
        return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.exception("Error al predecir")
        return Response({"error": f"Error al ejecutar el modelo: {e}"},
                         status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    precio_total = pred_m2 * datos["surface_total"]

    return Response({
        "precio_estimado_m2": round(pred_m2, 1),
        "precio_total_estimado": round(precio_total, 0),
        "moneda": "USD",
        "input": datos,
    })


@api_view(["POST"])
@parser_classes([MultiPartParser])
def cargar_csv(request):
    """
    POST /api/cargar-csv/  (multipart/form-data, campo "archivo")

    Sube un CSV con propiedades adicionales. Columnas mínimas: barrio (o l3),
    surface_total, price. El resto de las columnas (rooms, bathrooms,
    amenities, price_m2, etc.) son opcionales; price_m2 se calcula si falta.
    """
    archivo = request.FILES.get("archivo")
    if not archivo:
        return Response({"error": "No se envió ningún archivo (campo 'archivo')."},
                         status=status.HTTP_400_BAD_REQUEST)

    if not archivo.name.lower().endswith(".csv"):
        return Response({"error": "El archivo debe ser un .csv"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        contenido = archivo.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return Response({"error": "No se pudo leer el archivo. Verificá que sea un CSV en UTF-8."},
                         status=status.HTTP_400_BAD_REQUEST)

    try:
        df = pd.read_csv(io.StringIO(contenido))
    except Exception as e:
        return Response({"error": f"No se pudo parsear el CSV: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    if "barrio" not in df.columns and "l3" in df.columns:
        df = df.rename(columns={"l3": "barrio"})

    columnas_requeridas = {"barrio", "surface_total", "price"}
    faltantes = columnas_requeridas - set(df.columns)
    if faltantes:
        return Response(
            {"error": f"Al CSV le faltan columnas obligatorias: {sorted(faltantes)}. "
                      f"Columnas mínimas requeridas: {sorted(columnas_requeridas)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    creadas = 0
    errores = []
    nuevos_objetos = []

    for idx, row in df.iterrows():
        try:
            barrio = str(row.get("barrio", "")).strip()
            if not barrio or barrio.lower() == "nan":
                errores.append(f"Fila {idx + 2}: barrio vacío, se omite.")
                continue

            surface_total = row.get("surface_total")
            price = row.get("price")
            if pd.isna(surface_total) or pd.isna(price):
                errores.append(f"Fila {idx + 2}: surface_total o price vacío, se omite.")
                continue

            surface_total = float(surface_total)
            price = float(price)
            price_m2_raw = row.get("price_m2")
            price_m2 = float(price_m2_raw) if not pd.isna(price_m2_raw) else (
                round(price / surface_total, 2) if surface_total else None
            )

            id_raw = row.get("id")
            external_id = int(id_raw) if id_raw is not None and not pd.isna(id_raw) else None

            nuevos_objetos.append(Propiedad(
                external_id=external_id,
                barrio=barrio,
                rooms=_safe_float(row.get("rooms")),
                bedrooms=_safe_float(row.get("bedrooms")),
                bathrooms=_safe_float(row.get("bathrooms")),
                surface_total=surface_total,
                surface_covered=_safe_float(row.get("surface_covered")),
                price=price,
                price_m2=price_m2,
                property_type=row.get("property_type") or "Departamento",
                amenity_garage=_to_bool(row.get("amenity_garage")),
                amenity_pool=_to_bool(row.get("amenity_pool")),
                amenity_security=_to_bool(row.get("amenity_security")),
                is_luminous=_to_bool(row.get("is_luminous")),
                near_transport=_to_bool(row.get("near_transport")),
                is_a_estrenar=_to_bool(row.get("is_a_estrenar")),
                is_reciclado=_to_bool(row.get("is_reciclado")),
            ))
            creadas += 1
        except Exception as e:
            errores.append(f"Fila {idx + 2}: {e}")

    Propiedad.objects.bulk_create(nuevos_objetos, batch_size=1000)

    return Response({
        "mensaje": f"Carga completada. {creadas} propiedades agregadas.",
        "filas_creadas": creadas,
        "filas_con_error": len(errores),
        "detalle_errores": errores[:50],
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def info_modelo(request):
    """GET /api/modelo-info/ — metadata del modelo entrenado (métricas, features, barrios)."""
    return Response(get_metadata())
