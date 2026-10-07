"""
Gráficos estáticos de apoyo al análisis (complementan la animación).

Genera en output/figures/:
  - correlacion_por_anio.png : correlación transversal ingreso-bienestar por año
  - cambios_largo_plazo.png  : variación de largo plazo del ingreso vs. del
                               bienestar por país (primer vs. último año)

Estos gráficos sustentan, con asociaciones (no causalidad), la respuesta a la
pregunta del proyecto. Uso:
    python3 src/graficos.py
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

import analisis
import config as cfg
import regiones


def grafico_correlacion_por_anio(resumen) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.plot(resumen["year"], resumen["corr_pearson_gdp_ladder"],
            "-o", color="#0072B2", lw=2, label="Pearson")
    ax.plot(resumen["year"], resumen["corr_spearman_gdp_ladder"],
            "--s", color="#D55E00", lw=2, label="Spearman")
    ax.set_ylim(0, 1)
    ax.set_xlabel("Año")
    ax.set_ylabel("Correlación transversal\n(Log PIB per cápita vs Life Ladder)")
    ax.set_title("Asociación transversal ingreso–bienestar, estable y positiva "
                 "en todos los años", fontsize=12.5, fontweight="bold")
    ax.grid(True, ls="--", alpha=0.4)
    ax.legend(title="Método")
    ax.text(0.5, 0.06,
            "Cada punto resume ~130 países de ese año. Mide asociación entre "
            "países, no efectos causales.",
            transform=ax.transAxes, ha="center", fontsize=8.5, color="#666")
    fig.tight_layout()
    out = cfg.FIGURES_DIR / "correlacion_por_anio.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"Gráfico: {out}")


def grafico_cambios_largo_plazo(cambios) -> None:
    d = cambios["tabla"].copy()
    d["region"] = d["pais"].map(regiones.PAIS_A_REGION)
    d["color"] = d["region"].map(regiones.COLOR_REGION)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.axhline(0, color="#888", lw=1)
    ax.axvline(0, color="#888", lw=1)
    ax.scatter(d["d_log_gdp"], d["d_life_ladder"], c=d["color"],
               s=55, alpha=0.75, edgecolors="white", linewidths=0.6)

    # Etiquetar algunos países destacados (extremos y conocidos).
    destacar = set(d.nlargest(4, "d_life_ladder")["pais"]) | \
        set(d.nsmallest(4, "d_life_ladder")["pais"]) | \
        set(d.nlargest(3, "d_log_gdp")["pais"]) | \
        {"China", "India", "United States", "Venezuela"}
    for _, r in d[d["pais"].isin(destacar)].iterrows():
        ax.annotate(r["pais"], (r["d_log_gdp"], r["d_life_ladder"]),
                    xytext=(4, 4), textcoords="offset points", fontsize=8.5,
                    fontweight="bold",
                    path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    ax.set_xlabel("Δ Log PIB per cápita  (último − primer año observado)")
    ax.set_ylabel("Δ Life Ladder  (último − primer año observado)")
    ax.set_title("Cambios de largo plazo: más ingreso NO siempre acompaña más "
                 "bienestar", fontsize=12.5, fontweight="bold")
    ax.grid(True, ls="--", alpha=0.35)

    c = cambios["cuadrantes"]
    nota = (f"Correlación Δingreso–Δbienestar = {cambios['corr_cambios']:.2f}  ·  "
            f"ingreso↑bienestar↑: {c['ambos_suben']}   "
            f"ingreso↑bienestar↓: {c['ingreso_sube_bienestar_baja']}   "
            f"ingreso↓bienestar↑: {c['ingreso_baja_bienestar_sube']}   "
            f"ingreso↓bienestar↓: {c['ambos_bajan']}")
    fig.text(0.5, 0.01, nota, ha="center", fontsize=8.5, color="#555")
    # Leyenda de regiones.
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker="o", color="w", label=r,
               markerfacecolor=regiones.COLOR_REGION[r], markersize=9,
               markeredgecolor="white") for r in regiones.REGIONES]
    ax.legend(handles=handles, fontsize=8, loc="lower right", framealpha=0.9)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out = cfg.FIGURES_DIR / "cambios_largo_plazo.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"Gráfico: {out}")


def main() -> None:
    cfg.asegurar_directorios()
    res = analisis.main()
    grafico_correlacion_por_anio(res["resumen"])
    grafico_cambios_largo_plazo(res["cambios"])


if __name__ == "__main__":
    main()
