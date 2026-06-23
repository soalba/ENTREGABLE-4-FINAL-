"""
Reproduce el entrenamiento del Entregable 3 (Gradient Boosting sobre price_m2)
para generar el pipeline .joblib que consumirá el backend Django.

Basado en ENTREGABLE_3.ipynb — mismas features, mismo filtro, mismos hiperparámetros.

Uso (parado en la carpeta backend/):
    python train_model.py

Requiere que dataset_listo.csv esté en la carpeta backend/ (se entrega junto
al proyecto). Tarda algunos minutos (Gradient Boosting con 400 estimadores).
Útil para regenerar el modelo si tu versión instalada de scikit-learn no es
exactamente la misma con la que se entrenó el .joblib provisto.
"""
import os

import joblib
import json
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(THIS_DIR, "dataset_listo.csv")
OUT_DIR = os.path.join(THIS_DIR, "ml_model")
os.makedirs(OUT_DIR, exist_ok=True)

print("Cargando dataset...")
df = pd.read_csv(CSV_PATH)
print(f"Dataset cargado: {df.shape[0]:,} filas | {df.shape[1]} columnas")

# dataset_listo.csv ya viene filtrado a ventas y con la columna renombrada a 'barrio'.
# Internamente mantenemos el nombre 'l3' para la feature categórica porque es
# el nombre con el que se entrenó el pipeline original (igual que en
# ENTREGABLE_3.ipynb) y el que usa el backend (propiedades/views.py) al armar
# la fila de predicción. Si el CSV trae 'barrio', se renombra a 'l3' acá.
if "operation_type" in df.columns:
    df = df[df["operation_type"] == "venta"].copy()
    print(f"Solo ventas: {len(df):,} filas")
if "barrio" in df.columns and "l3" not in df.columns:
    df = df.rename(columns={"barrio": "l3"})

BOOL_COLS = [
    "amenity_garage", "amenity_pool", "amenity_security",
    "is_luminous", "near_transport", "is_a_estrenar", "is_reciclado",
]
for c in BOOL_COLS:
    df[c] = df[c].astype(int)

TARGET = "price_m2"
NUM_FEATURES = [
    "surface_total", "rooms", "bathrooms",
    "amenity_garage", "amenity_pool", "amenity_security",
    "is_luminous", "near_transport", "is_a_estrenar", "is_reciclado",
]
CAT_FEATURES = ["l3"]
ALL_FEATURES = NUM_FEATURES + CAT_FEATURES

df_modelo = df[ALL_FEATURES + [TARGET]].dropna().copy()

q01 = df_modelo[TARGET].quantile(0.01)
q99 = df_modelo[TARGET].quantile(0.99)
df_modelo = df_modelo[(df_modelo[TARGET] >= q01) & (df_modelo[TARGET] <= q99)]
print(f"Filas para modelado (tras dropna + filtro outliers p1-p99): {len(df_modelo):,}")

X = df_modelo[ALL_FEATURES]
y = df_modelo[TARGET]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), NUM_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT_FEATURES),
    ]
)

pipe_gb = Pipeline([
    ("preprocessor", preprocessor),
    ("model", GradientBoostingRegressor(
        n_estimators=400, learning_rate=0.05, max_depth=5,
        min_samples_leaf=15, subsample=0.8, random_state=42,
    )),
])

print("Entrenando Gradient Boosting (400 estimadores, lr=0.05)... esto puede tardar varios minutos")
pipe_gb.fit(X_train, y_train)

y_pred = pipe_gb.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)
mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100

print(f"\nMAE:  {mae:.1f} USD/m2")
print(f"RMSE: {rmse:.1f} USD/m2")
print(f"R2:   {r2:.4f}")
print(f"MAPE: {mape:.2f}%")

joblib.dump(pipe_gb, os.path.join(OUT_DIR, "pipeline_gradient_boosting.joblib"))
print(f"\n✓ Pipeline guardado en {OUT_DIR}/pipeline_gradient_boosting.joblib")

barrios = sorted(df_modelo["l3"].unique().tolist())

metadata = {
    "modelo": "Gradient Boosting Regressor",
    "target": TARGET,
    "features_numericas": NUM_FEATURES,
    "feature_categorica": CAT_FEATURES,
    "barrios": barrios,
    "metricas_test": {"MAE": round(mae, 1), "RMSE": round(rmse, 1), "R2": round(r2, 4), "MAPE": round(mape, 2)},
    "n_train": len(X_train),
    "n_test": len(X_test),
    "filtro": "operation_type == venta, dropna en features clave, outliers price_m2 p1-p99 removidos",
}
with open(os.path.join(OUT_DIR, "metadata.json"), "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)
print("✓ metadata.json guardado")
print(f"✓ {len(barrios)} barrios disponibles")
