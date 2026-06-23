"""
Carga perezosa (lazy) y cacheada del pipeline de Machine Learning entrenado
en el Entregable 3 (Gradient Boosting Regressor sobre price_m2).

Se mantiene una única instancia en memoria del pipeline para no leer el
archivo .joblib en cada request.
"""
import json
import threading

import joblib
from django.conf import settings

_lock = threading.Lock()
_pipeline = None
_metadata = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        with _lock:
            if _pipeline is None:
                if not settings.ML_MODEL_PATH.exists():
                    raise FileNotFoundError(
                        f"No se encontró el modelo entrenado en {settings.ML_MODEL_PATH}. "
                        "Ejecutá train_model.py o copiá el .joblib provisto en backend/ml_model/."
                    )
                try:
                    _pipeline = joblib.load(settings.ML_MODEL_PATH)
                except Exception as e:
                    raise RuntimeError(
                        "No se pudo cargar el modelo entrenado "
                        f"({settings.ML_MODEL_PATH.name}). Esto suele pasar cuando la versión "
                        "de scikit-learn instalada no coincide con la usada al entrenar el "
                        "modelo. Solución: parate en la carpeta backend/ y corré "
                        "`python train_model.py` para regenerarlo con tu versión actual "
                        f"(detalle técnico: {e})"
                    ) from e
    return _pipeline


def get_metadata():
    global _metadata
    if _metadata is None:
        with _lock:
            if _metadata is None:
                if settings.ML_METADATA_PATH.exists():
                    with open(settings.ML_METADATA_PATH, encoding="utf-8") as f:
                        _metadata = json.load(f)
                else:
                    _metadata = {}
    return _metadata


def get_barrios_validos():
    meta = get_metadata()
    return meta.get("barrios", [])
