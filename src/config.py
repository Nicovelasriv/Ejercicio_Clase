"""
Configuración central del proyecto.

Rutas y constantes compartidas por todos los scripts de ``src/``.
Centralizar aquí permite ejecutar el proyecto desde cualquier directorio
y reproducirlo de principio a fin sin rutas "quemadas" en cada script.
"""

from pathlib import Path

# --- Rutas base -------------------------------------------------------------
# config.py vive en src/, por lo que la raíz del proyecto es su carpeta padre.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
FIGURES_DIR = OUTPUT_DIR / "figures"

# Archivo de datos crudo (descargado desde el repositorio original).
RAW_CSV = DATA_DIR / "world-happiness-report.csv"
DATA_URL = (
    "https://raw.githubusercontent.com/Andres1984/Data-Analysis-with-R/"
    "refs/heads/master/Bases/world-happiness-report.csv"
)

# --- Archivos de salida -----------------------------------------------------
VIDEO_OUT = OUTPUT_DIR / "video_final.mp4"
RESUMEN_CSV = OUTPUT_DIR / "resumen_datos.csv"
CLEANED_CSV = OUTPUT_DIR / "datos_limpios_animacion.csv"
REPORTE_MD = OUTPUT_DIR / "reporte_analisis.md"

# --- Variables de la visualización (deben existir en la base) ---------------
# NO se inventan variables: estos nombres se validan contra el CSV al cargar.
COL_PAIS = "Country name"
COL_ANIO = "year"
COL_X = "Log GDP per capita"              # eje X
COL_Y = "Life Ladder"                      # eje Y
COL_TAM = "Healthy life expectancy at birth"  # tamaño de la burbuja

# Las cuatro variables imprescindibles para dibujar una burbuja.
VARS_ANIMACION = [COL_X, COL_Y, COL_TAM]

# --- Parámetros de la animación ---------------------------------------------
FPS = 20                 # cuadros por segundo de reproducción
SEGUNDOS_POR_ANIO = 2.0  # tiempo que cada año permanece en pantalla
PAUSA_INICIO_FIN = 1.2   # pausa extra (s) en el primer y último año
DPI = 150                # resolución de render (150 dpi * figsize -> píxeles)
FIGSIZE = (12.8, 7.2)    # 1920x1080 aprox. a 150 dpi


def asegurar_directorios() -> None:
    """Crea las carpetas de salida si no existen (idempotente)."""
    for d in (DATA_DIR, OUTPUT_DIR, FIGURES_DIR):
        d.mkdir(parents=True, exist_ok=True)


def descargar_si_falta(force: bool = False) -> None:
    """Descarga el CSV a ``data/`` si no existe (para correr desde cero).

    Usa ``urllib`` (respeta las variables de entorno de proxy). Si falla,
    intenta con ``curl`` como alternativa.
    """
    asegurar_directorios()
    if RAW_CSV.exists() and not force:
        return
    import urllib.request
    print(f"Descargando base -> {RAW_CSV} ...")
    try:
        urllib.request.urlretrieve(DATA_URL, RAW_CSV)
    except Exception as exc:  # pragma: no cover - ruta de respaldo
        import shutil
        import subprocess
        if shutil.which("curl") is None:
            raise RuntimeError(
                f"No se pudo descargar la base ({exc}). Descárgala manualmente:\n"
                f"  curl -sS -o '{RAW_CSV}' '{DATA_URL}'"
            ) from exc
        subprocess.run(["curl", "-sS", "-o", str(RAW_CSV), DATA_URL], check=True)
    print(f"Descarga completa ({RAW_CSV.stat().st_size} bytes).")
