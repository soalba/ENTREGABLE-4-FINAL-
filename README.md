# Plano — Buscador de departamentos en CABA

Trabajo final de Ciencia de Datos Aplicada (ITBA) — Entregable 4: despliegue y
presentación de la solución.

Aplicación full-stack que expone el modelo de Machine Learning del
**Entregable 3** (Gradient Boosting Regressor sobre `price_m2`) a través de
una API REST en Django, con un frontend propio (HTML/CSS/JS, sin frameworks)
para buscar departamentos en CABA con filtros, estimar precios, visualizar de
dónde salen esos precios y cargar nuevos datos vía CSV.

**Corre 100% en local. No necesita conexión a internet ni servicios externos.**

---

## 1. Qué incluye este proyecto

```
backend/
├── manage.py
├── requirements.txt
├── dataset_listo.csv          ← dataset limpio (76.202 deptos en venta, CABA)
├── db.sqlite3                 ← base de datos ya cargada y lista para usar
├── train_model.py             ← script para (re)entrenar el modelo
├── ml_model/
│   ├── pipeline_gradient_boosting.joblib   ← modelo entrenado (Entregable 3)
│   └── metadata.json                        ← métricas, features, barrios
├── inmobiliaria/               ← configuración del proyecto Django
├── propiedades/                ← app Django: modelos, API, comando de carga
├── templates/index.html        ← frontend (SPA de una sola página)
└── static/
    ├── css/styles.css
    ├── js/app.js
    ├── js/chart.umd.js         ← Chart.js vendorizado (sin CDN externo)
    └── img/logo.svg
```

La base SQLite ya viene cargada con las 76.202 propiedades del dataset, así
que **no hace falta importar nada para arrancar a usar la app**. El paso de
importación de CSV se deja documentado más abajo igual, por si querés
regenerarla desde cero o usarla como referencia para el módulo de carga.

---

## 2. Instalación

Requisitos: **Python 3.11 o superior** (recomendado 3.11–3.13).

```bash
cd backend

# Crear y activar un entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate          # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

> **Nota sobre versiones de Python:** el modelo entregado
> (`pipeline_gradient_boosting.joblib`) fue entrenado con `scikit-learn
> 1.8.0`, que requiere Python 3.11+. Si tenés una versión de Python más
> vieja, o si al cargar el modelo ves un error de incompatibilidad de
> versión, corré `python train_model.py` (sección 5) para regenerar el
> modelo con tu propia versión de scikit-learn — tarda 1-2 minutos y deja
> todo funcionando igual.

---

## 3. Correr la aplicación

```bash
cd backend
python manage.py runserver
```

Abrí el navegador en **http://localhost:8000/** — ahí está todo: buscador,
estimador, panel de mercado y carga de CSV, en una sola página con pestañas.

La API REST queda disponible en `http://localhost:8000/api/` (ver sección 6).

(Opcional) Panel de administración de Django, para ver/editar propiedades
directamente:

```bash
python manage.py createsuperuser
# seguís las instrucciones, después entrás a http://localhost:8000/admin/
```

---

## 4. Los 4 módulos de la aplicación

1. **Buscador** — filtros combinables por barrio, precio, ambientes, baños,
   superficie y amenities (cochera, pileta, seguridad, luminosidad, cercanía
   a transporte, a estrenar, reciclado). Resultados paginados, con orden por
   precio o superficie.

2. **Estimador de precio** — formulario con las características de un
   departamento (barrio, superficie, ambientes, baños, amenities). Llama al
   endpoint `/api/predecir/`, que corre el pipeline de Gradient Boosting y
   devuelve el precio estimado por m² y el precio total.

3. **Panel de mercado** — gráficos (Chart.js) equivalentes a los del
   Entregable 3: precio mediano por barrio, importancia de variables del
   modelo (de dónde "sale" el precio) y distribución de precios por m².
   Pensado para que el usuario entienda el origen de las estimaciones, no
   solo el número final.

4. **Cargar datos** — sube un CSV con propiedades adicionales (arrastrar y
   soltar o seleccionar archivo) y las agrega a la base local. Valida columnas
   obligatorias, informa filas con error y no rompe la carga si algunas filas
   están incompletas.

---

## 5. Reentrenar el modelo (opcional)

El modelo ya viene entrenado y guardado en
`ml_model/pipeline_gradient_boosting.joblib`. Sólo hace falta reentrenarlo si:

- Tu versión de scikit-learn no puede cargar el `.joblib` provisto (ver nota
  en la sección 2), o
- Querés volver a generarlo después de cargar muchos datos nuevos vía CSV.

```bash
cd backend
python train_model.py
```

Reproduce exactamente el pipeline del Entregable 3 (mismas features,
mismo filtro de outliers p1–p99, mismos hiperparámetros de
`GradientBoostingRegressor`). Tarda entre 1 y 3 minutos según la máquina.

> Si reentrenás después de cargar datos nuevos por CSV desde la app, primero
> hay que regenerar `dataset_listo.csv` o apuntar `train_model.py` a la base
> actual — el script, tal como está, entrena sobre el CSV original. Para
> incorporar datos cargados vía la interfaz al entrenamiento, lo más simple
> es exportar la tabla `Propiedad` a CSV (`python manage.py dumpdata` o una
> consulta directa) y usarla como fuente.

---

## 6. Reconstruir la base de datos desde cero (opcional)

Si por algún motivo borrás `db.sqlite3` o querés partir de cero:

```bash
cd backend
python manage.py migrate
python manage.py import_csv
```

`import_csv` lee `dataset_listo.csv` por defecto. También podés apuntarlo a
otro archivo:

```bash
python manage.py import_csv --path otro_archivo.csv
python manage.py import_csv --reset    # borra los datos existentes antes de importar
```

---

## 7. API REST — referencia rápida

Todos los endpoints están bajo `/api/`. Respuestas en JSON.

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/propiedades/` | GET | Lista paginada de propiedades, con filtros (ver abajo) |
| `/api/barrios/` | GET | Barrios disponibles, con cantidad de propiedades cada uno |
| `/api/estadisticas/` | GET | Datos agregados para los gráficos (precio por barrio, distribución, importancia de variables) |
| `/api/predecir/` | POST | Estima el precio de una propiedad nueva |
| `/api/cargar-csv/` | POST | Sube un CSV (`multipart/form-data`, campo `archivo`) y agrega propiedades |
| `/api/modelo-info/` | GET | Metadata del modelo: métricas de test, features, barrios soportados |

### Filtros de `/api/propiedades/` (query params, todos opcionales)

- `barrio` (repetible): `?barrio=Palermo&barrio=Almagro`
- `precio_min`, `precio_max`: rango de precio total (USD)
- `ambientes_min`, `ambientes_max`: rango de cantidad de ambientes
- `banios_min`: mínimo de baños
- `superficie_min`, `superficie_max`: rango de superficie total (m²)
- `garage`, `pileta`, `seguridad`, `luminoso`, `cerca_transporte`,
  `a_estrenar`, `reciclado`: `true` para filtrar por ese amenity
- `ordenar`: `price`, `-price`, `surface_total`, `-surface_total`, etc.
- `page`, `page_size`: paginación (default 24 por página)

Ejemplo:

```
GET /api/propiedades/?barrio=Palermo&precio_max=200000&pileta=true&ordenar=price
```

### Body de `/api/predecir/`

```json
{
  "barrio": "Palermo",
  "surface_total": 65,
  "rooms": 3,
  "bathrooms": 1,
  "amenity_garage": false,
  "amenity_pool": false,
  "amenity_security": true,
  "is_luminous": true,
  "near_transport": true,
  "is_a_estrenar": false,
  "is_reciclado": false
}
```

Respuesta:

```json
{
  "precio_estimado_m2": 2963.3,
  "precio_total_estimado": 192612.0,
  "moneda": "USD",
  "input": { ... }
}
```

---

## 8. Decisiones técnicas (para la presentación oral)

- **Backend**: Django + Django REST Framework. Separación clara entre la capa
  de modelo de datos (`propiedades/models.py`), la capa de ML
  (`propiedades/ml.py`, que carga el pipeline una sola vez en memoria) y la
  capa de servicio HTTP (`propiedades/views.py`).
- **Modelo**: se reutiliza tal cual el pipeline `Gradient Boosting` entrenado
  en el Entregable 3 (mismo preprocesamiento — `StandardScaler` +
  `OneHotEncoder` —, mismos hiperparámetros), persistido con `joblib`.
- **Base de datos**: SQLite, sin dependencias externas, para que el proyecto
  corra con un único `runserver` y no requiera levantar un motor de base de
  datos aparte.
- **Frontend**: HTML/CSS/JS sin build step ni Node.js, servido directamente
  por Django como archivos estáticos + un template. Consume la API vía
  `fetch`. Chart.js está vendorizado localmente (no depende de un CDN), para
  garantizar que la app funcione sin conexión a internet.
- **Carga de CSV**: valida columnas obligatorias, tolera columnas faltantes
  opcionales, calcula `price_m2` automáticamente si no viene en el archivo, y
  reporta filas descartadas sin interrumpir la carga del resto.
- **Manejo de errores**: la API responde con códigos HTTP apropiados (400
  para datos inválidos, 503 si el modelo no está disponible, 500 para errores
  inesperados) y mensajes descriptivos en español.

---

## 9. Métricas del modelo (Entregable 3)

| Métrica | Valor (test set) |
|---|---|
| MAE | ≈ 424 USD/m² |
| RMSE | ≈ 580 USD/m² |
| R² | ≈ 0.63 |
| MAPE | ≈ 15.5% |

El barrio es, de lejos, la variable más importante (≈47% de la importancia
agregada del modelo), seguido por superficie, baños y amenities premium
(pileta, seguridad). Esto se puede ver en vivo en el módulo **Panel de
mercado** de la aplicación.
