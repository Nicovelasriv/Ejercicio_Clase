"""
Inspección de la base World Happiness Report (fase "ANTES DE PROGRAMAR").

Carga la base, examina su estructura y reporta:
  - número de observaciones
  - número de países
  - rango de años
  - variables y tipos de datos
  - valores faltantes (por variable y por año)

También documenta la estrategia de limpieza y produce el conjunto de datos
que usará la animación. No realiza imputaciones: los faltantes se tratan por
eliminación de filas (listwise) únicamente sobre las variables que se grafican.

Uso:
    python3 src/inspeccion_datos.py
"""

from __future__ import annotations

import sys

import pandas as pd

import config as cfg


def cargar_datos() -> pd.DataFrame:
    """Carga el CSV crudo validando que existan las columnas esperadas.

    Se usa ``encoding='utf-8-sig'`` porque el archivo original trae un BOM
    al inicio (﻿) que, de otro modo, se adhiere al nombre de la primera
    columna ("Country name").
    """
    cfg.descargar_si_falta()
    if not cfg.RAW_CSV.exists():
        sys.exit(
            f"No se encontró {cfg.RAW_CSV}.\n"
            f"Descárgala con:\n  curl -sS -o '{cfg.RAW_CSV}' '{cfg.DATA_URL}'"
        )

    df = pd.read_csv(cfg.RAW_CSV, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    faltan = [c for c in (cfg.COL_PAIS, cfg.COL_ANIO, *cfg.VARS_ANIMACION)
              if c not in df.columns]
    if faltan:
        sys.exit(f"La base no contiene las columnas esperadas: {faltan}")
    return df


def inspeccionar(df: pd.DataFrame) -> dict:
    """Imprime un reporte de estructura y devuelve métricas clave en un dict."""
    print("=" * 70)
    print("INSPECCIÓN DE LA BASE  —  World Happiness Report")
    print("=" * 70)

    n_obs = len(df)
    n_paises = df[cfg.COL_PAIS].nunique()
    anio_min, anio_max = int(df[cfg.COL_ANIO].min()), int(df[cfg.COL_ANIO].max())

    print(f"\nObservaciones (filas) : {n_obs}")
    print(f"Países únicos         : {n_paises}")
    print(f"Rango de años         : {anio_min} – {anio_max} "
          f"({df[cfg.COL_ANIO].nunique()} años distintos)")

    print("\n--- Variables y tipos de dato -------------------------------------")
    for col in df.columns:
        print(f"  {col:<38} {str(df[col].dtype)}")

    print("\n--- Estadísticos descriptivos (variables numéricas) ---------------")
    with pd.option_context("display.width", 120, "display.max_columns", None):
        print(df.describe().round(3).to_string())

    print("\n--- Valores faltantes por variable --------------------------------")
    na = df.isna().sum()
    na_pct = (df.isna().mean() * 100).round(2)
    tabla_na = pd.DataFrame({"n_faltantes": na, "pct_faltantes": na_pct})
    print(tabla_na.to_string())

    # Faltantes específicos en las variables de la animación.
    print("\n--- Faltantes en las variables de la animación --------------------")
    print(f"  Eje X   ({cfg.COL_X}): {int(df[cfg.COL_X].isna().sum())}")
    print(f"  Eje Y   ({cfg.COL_Y}): {int(df[cfg.COL_Y].isna().sum())}")
    print(f"  Tamaño  ({cfg.COL_TAM}): {int(df[cfg.COL_TAM].isna().sum())}")

    # Observaciones por año (cobertura) y faltantes por año.
    print("\n--- Cobertura por año (n de países con las 4 variables completas) --")
    completos = df.dropna(subset=cfg.VARS_ANIMACION)
    cob = (
        df.groupby(cfg.COL_ANIO)[cfg.COL_PAIS].nunique().rename("paises_total")
        .to_frame()
        .join(
            completos.groupby(cfg.COL_ANIO)[cfg.COL_PAIS]
            .nunique().rename("paises_completos")
        )
    )
    print(cob.to_string())

    n_dup = int(df.duplicated(subset=[cfg.COL_PAIS, cfg.COL_ANIO]).sum())
    print(f"\nFilas duplicadas (país, año): {n_dup}")

    return {
        "n_obs": n_obs,
        "n_paises": n_paises,
        "anio_min": anio_min,
        "anio_max": anio_max,
        "n_anios": int(df[cfg.COL_ANIO].nunique()),
        "na_por_variable": tabla_na,
        "cobertura_por_anio": cob,
        "n_duplicados": n_dup,
    }


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica la estrategia de limpieza documentada y devuelve el df limpio.

    Decisiones (ver reporte_analisis.md / README.md):
      1. Normalizar nombres de columna (quitar espacios y BOM).
      2. Eliminar duplicados exactos de (país, año) si existieran.
      3. Para la animación, conservar sólo filas con las 4 variables que se
         grafican completas (eje X, eje Y, tamaño). NO se imputa: una burbuja
         requiere coordenadas y tamaño reales; inventarlos distorsionaría la
         lectura. Las variables NO graficadas (p. ej. Generosity) pueden tener
         faltantes sin afectar la figura, por eso no se usan como criterio.
      4. Ordenar por país y año para animaciones y cálculos reproducibles.
    """
    antes = len(df)
    df = df.drop_duplicates(subset=[cfg.COL_PAIS, cfg.COL_ANIO])
    sin_dup = len(df)

    limpio = df.dropna(subset=cfg.VARS_ANIMACION).copy()
    limpio = limpio.sort_values([cfg.COL_PAIS, cfg.COL_ANIO]).reset_index(drop=True)

    print("\n--- Resultado de la limpieza --------------------------------------")
    print(f"  Filas originales                    : {antes}")
    print(f"  Tras eliminar duplicados (país, año): {sin_dup}  "
          f"(-{antes - sin_dup})")
    print(f"  Tras exigir X, Y y tamaño completos : {len(limpio)}  "
          f"(-{sin_dup - len(limpio)})")
    print(f"  Países en el dataset limpio         : "
          f"{limpio[cfg.COL_PAIS].nunique()}")
    print(f"  Rango de años (limpio)              : "
          f"{int(limpio[cfg.COL_ANIO].min())}–{int(limpio[cfg.COL_ANIO].max())}")
    return limpio


def main() -> pd.DataFrame:
    cfg.asegurar_directorios()
    df = cargar_datos()
    inspeccionar(df)
    limpio = limpiar(df)
    limpio.to_csv(cfg.CLEANED_CSV, index=False, encoding="utf-8")
    print(f"\nDataset limpio guardado en: {cfg.CLEANED_CSV}")
    return limpio


if __name__ == "__main__":
    main()
