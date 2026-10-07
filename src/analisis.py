"""
Análisis descriptivo que responde a la pregunta del proyecto:

  ¿La evolución del ingreso de los países a través del tiempo está
   acompañada por cambios en sus niveles de bienestar?

Se usan aproximaciones DESCRIPTIVAS y de ASOCIACIÓN (no causales):
  1. Asociación transversal por año entre el ingreso (Log GDP per capita) y
     el bienestar (Life Ladder): correlaciones de Pearson y Spearman.
  2. Asociación intrapaís a lo largo del tiempo: para cada país con suficientes
     años, correlación temporal entre su ingreso y su bienestar.
  3. Cambios de largo plazo: variación (último - primer año observado) del
     ingreso vs. del bienestar por país, y su correlación.

Genera ``output/resumen_datos.csv`` (resumen por año) y devuelve un dict con
los números que alimentan ``reporte_analisis.md``.

Uso:
    python3 src/analisis.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config as cfg

MIN_ANIOS_INTRAPAIS = 8  # años mínimos por país para la correlación temporal


def _spearman(a: pd.Series, b: pd.Series) -> float:
    """Spearman = Pearson sobre los rangos (evita depender de scipy)."""
    return a.rank().corr(b.rank(), method="pearson")


def cargar_limpio() -> pd.DataFrame:
    """Carga el dataset limpio; si no existe, lo genera con inspeccion_datos."""
    if not cfg.CLEANED_CSV.exists():
        import inspeccion_datos
        return inspeccion_datos.main()
    return pd.read_csv(cfg.CLEANED_CSV, encoding="utf-8")


def resumen_por_anio(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla resumen por año con tamaños, promedios y correlaciones."""
    filas = []
    for anio, g in df.groupby(cfg.COL_ANIO):
        filas.append({
            "year": int(anio),
            "n_paises": int(g[cfg.COL_PAIS].nunique()),
            "log_gdp_media": g[cfg.COL_X].mean(),
            "log_gdp_mediana": g[cfg.COL_X].median(),
            "life_ladder_media": g[cfg.COL_Y].mean(),
            "life_ladder_mediana": g[cfg.COL_Y].median(),
            "healthy_life_media": g[cfg.COL_TAM].mean(),
            "corr_pearson_gdp_ladder": g[cfg.COL_X].corr(g[cfg.COL_Y], method="pearson"),
            "corr_spearman_gdp_ladder": _spearman(g[cfg.COL_X], g[cfg.COL_Y]),
        })
    res = pd.DataFrame(filas).sort_values("year").reset_index(drop=True)
    return res.round(4)


def asociacion_intrapais(df: pd.DataFrame) -> dict:
    """Correlación temporal ingreso-bienestar dentro de cada país."""
    corrs = {}
    for pais, g in df.groupby(cfg.COL_PAIS):
        g = g.sort_values(cfg.COL_ANIO)
        if g[cfg.COL_ANIO].nunique() >= MIN_ANIOS_INTRAPAIS:
            r = g[cfg.COL_X].corr(g[cfg.COL_Y])
            if pd.notna(r):
                corrs[pais] = r
    serie = pd.Series(corrs)
    return {
        "n_paises_evaluados": int(serie.size),
        "corr_mediana": float(serie.median()),
        "corr_media": float(serie.mean()),
        "pct_positiva": float((serie > 0).mean() * 100),
        "pct_negativa": float((serie < 0).mean() * 100),
        "serie": serie,
    }


def cambios_largo_plazo(df: pd.DataFrame) -> dict:
    """Variación primer->último año por país del ingreso vs. del bienestar."""
    filas = []
    for pais, g in df.groupby(cfg.COL_PAIS):
        g = g.sort_values(cfg.COL_ANIO)
        if g[cfg.COL_ANIO].nunique() < 2:
            continue
        prim, ult = g.iloc[0], g.iloc[-1]
        span = int(ult[cfg.COL_ANIO] - prim[cfg.COL_ANIO])
        if span <= 0:
            continue
        filas.append({
            "pais": pais,
            "anios": span,
            "d_log_gdp": ult[cfg.COL_X] - prim[cfg.COL_X],
            "d_life_ladder": ult[cfg.COL_Y] - prim[cfg.COL_Y],
        })
    d = pd.DataFrame(filas)
    corr = d["d_log_gdp"].corr(d["d_life_ladder"])
    # Cuadrantes: ¿subió/bajó el ingreso junto con el bienestar?
    cuad = {
        "ambos_suben": int(((d.d_log_gdp > 0) & (d.d_life_ladder > 0)).sum()),
        "ingreso_sube_bienestar_baja": int(((d.d_log_gdp > 0) & (d.d_life_ladder < 0)).sum()),
        "ingreso_baja_bienestar_sube": int(((d.d_log_gdp < 0) & (d.d_life_ladder > 0)).sum()),
        "ambos_bajan": int(((d.d_log_gdp < 0) & (d.d_life_ladder < 0)).sum()),
    }
    return {
        "n_paises": int(len(d)),
        "corr_cambios": float(corr),
        "cuadrantes": cuad,
        "tabla": d.sort_values("d_log_gdp"),
    }


def main() -> dict:
    cfg.asegurar_directorios()
    df = cargar_limpio()

    resumen = resumen_por_anio(df)
    resumen.to_csv(cfg.RESUMEN_CSV, index=False, encoding="utf-8")

    pooled_pearson = df[cfg.COL_X].corr(df[cfg.COL_Y], method="pearson")
    pooled_spearman = _spearman(df[cfg.COL_X], df[cfg.COL_Y])

    intra = asociacion_intrapais(df)
    cambios = cambios_largo_plazo(df)

    print("=" * 70)
    print("ANÁLISIS DESCRIPTIVO  (asociaciones, NO causalidad)")
    print("=" * 70)
    print("\n--- Resumen por año (guardado en resumen_datos.csv) ---")
    print(resumen.to_string(index=False))

    print(f"\nAsociación transversal agrupada (todas las obs.):")
    print(f"  Pearson  Log GDP vs Life Ladder : {pooled_pearson:.3f}")
    print(f"  Spearman Log GDP vs Life Ladder : {pooled_spearman:.3f}")
    print(f"  Correlación transversal por año: de "
          f"{resumen.corr_pearson_gdp_ladder.min():.3f} a "
          f"{resumen.corr_pearson_gdp_ladder.max():.3f} "
          f"(mediana {resumen.corr_pearson_gdp_ladder.median():.3f})")

    print(f"\nAsociación INTRAPAÍS a lo largo del tiempo "
          f"(>= {MIN_ANIOS_INTRAPAIS} años, n={intra['n_paises_evaluados']} países):")
    print(f"  Correlación temporal mediana : {intra['corr_mediana']:.3f}")
    print(f"  Correlación temporal media   : {intra['corr_media']:.3f}")
    print(f"  % países con asociación positiva: {intra['pct_positiva']:.1f}%")
    print(f"  % países con asociación negativa: {intra['pct_negativa']:.1f}%")

    print(f"\nCambios de largo plazo (primer vs. último año, "
          f"n={cambios['n_paises']} países):")
    print(f"  Correlación Δingreso vs Δbienestar: {cambios['corr_cambios']:.3f}")
    c = cambios["cuadrantes"]
    print(f"  Ingreso ↑ y bienestar ↑ : {c['ambos_suben']}")
    print(f"  Ingreso ↑ y bienestar ↓ : {c['ingreso_sube_bienestar_baja']}")
    print(f"  Ingreso ↓ y bienestar ↑ : {c['ingreso_baja_bienestar_sube']}")
    print(f"  Ingreso ↓ y bienestar ↓ : {c['ambos_bajan']}")

    return {
        "resumen": resumen,
        "pooled_pearson": pooled_pearson,
        "pooled_spearman": pooled_spearman,
        "intra": intra,
        "cambios": cambios,
        "n_paises_limpio": int(df[cfg.COL_PAIS].nunique()),
        "anio_min": int(df[cfg.COL_ANIO].min()),
        "anio_max": int(df[cfg.COL_ANIO].max()),
        "n_obs_limpio": int(len(df)),
    }


if __name__ == "__main__":
    main()
