# Cobranza y Cartera — App web (Streamlit)

Web con 2 apartados para que cualquier persona genere y descargue los reportes:

- **COBRANZA**: LATAM (10 bases) y PRESICO MX (7 bases). Procesos **Mañana** (día vencido + hoy = 2 archivos), **Tarde** (hoy) o **fecha específica**. Muestra el seguimiento en vivo por base, la tabla de montos por corte (País/Marca en LATAM, Unidad de Negocio en MX) y las **rutas que faltan por agregar a la Estructura**.
- **CARTERA**: siempre a día vencido (o fecha específica). Bloques LATAM y MÉXICO con seguimiento por base, validación de rutas y descargas (`LATAM.xlsx`, `PRESICO.xlsx`, `PRESICO.parquet`).

Los queries SQL son los mismos de Power Query, pegados tal cual (módulos `datos_*.py`). Nada depende de carpetas locales: los archivos se generan en memoria y se descargan desde el navegador.

## Archivos del proyecto

| Archivo | Qué es |
|---|---|
| `app.py` | La página web (archivo principal). |
| `procesos.py` | Motor de extracción y transformaciones (cobranza + cartera). |
| `datos_cobranza_latam.py` | Los 10 queries de cobranza LATAM tal cual + columnas. |
| `datos_cobranza_presico.py` | Los 7 queries de cobranza PRESICO MX tal cual + columnas. |
| `datos_cartera.py` | Servidores y columnas de cartera. |
| `TIPO DE CAMBIO.xlsx` | Tipo de cambio por país (se puede subir otro desde la página). |
| `Venta Cartera.xlsx` | Exclusiones de venta/inseguridad (se puede subir otro desde la página). |
| `.streamlit/config.toml` | Tema visual de la página (colores corporativos). |
| `requirements.txt` | Librerías que instala Streamlit Cloud. |

## Cómo publicarla en share.streamlit.io

1. Crea un repositorio en GitHub (recomendado **privado**) y sube TODOS los archivos de esta carpeta.
2. Entra a https://share.streamlit.io/ con tu cuenta de GitHub → **New app**.
3. Elige el repositorio, rama `main` y como archivo principal **`app.py`** → **Deploy**.
4. (Recomendado) En la app → **Settings → Secrets**, agrega las credenciales para no dejarlas en el código:
   ```toml
   DB_USER = "jtrejol"
   DB_PASSWORD = "xxxxxxxx"
   ```
   Si no configuras Secrets, usa las credenciales que ya vienen en `procesos.py`.

## Importante

- Los servidores RDS deben aceptar conexiones desde internet (igual que ya lo hacen con Power BI); si algún día restringen IPs, habría que permitir las de Streamlit Cloud.
- **Venta Cartera.xlsx** no viene en el repositorio: se sube desde la página cuando se genera la cartera (si no se sube, la cartera sale sin esas exclusiones y la página lo avisa).
- Para actualizar el **TIPO DE CAMBIO**: reemplaza el archivo del repositorio, o simplemente súbelo desde la página al momento de generar.
- Las fechas "hoy / día vencido" se calculan con hora de Ciudad de México.
