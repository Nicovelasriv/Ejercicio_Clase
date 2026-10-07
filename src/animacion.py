"""
Animación tipo Hans Rosling (gráfico de burbujas animado por año).

  Eje X   = Log GDP per capita        (ingreso)
  Eje Y   = Life Ladder               (bienestar subjetivo)
  Tamaño  = Healthy life expectancy at birth
  Color   = región (apoyo visual, ver regiones.py)
  Tiempo  = year  (un año por "paso"; cada año se sostiene varios cuadros
            para que la lectura sea cómoda, sin interpolar datos inventados)

Produce ``output/video_final.mp4`` y algunos cuadros estáticos de referencia
en ``output/figures/``.

Implementación: los elementos estáticos (títulos, leyenda, ejes) y los
artistas dinámicos (burbujas, etiquetas, estelas, año) se crean UNA sola vez;
en cada cuadro sólo se actualizan posiciones/tamaños/colores. Esto hace el
render ~10x más rápido que redibujar todo en cada cuadro, y garantiza que el
video y los PNG estáticos usen exactamente el mismo dibujo.

Uso:
    python3 src/animacion.py
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # backend sin pantalla, apto para render en servidor

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd

import config as cfg
import regiones

# --- Parámetros visuales ----------------------------------------------------
TAM_MIN, TAM_MAX = 35, 820      # área (pts^2) de la burbuja más chica / grande
PAD_X, PAD_Y = 0.35, 0.45       # margen añadido a los límites de los ejes
VENTANA_ESTELA = 6              # años recientes mostrados como "cola de cometa"
ALPHA_BURBUJA = 0.62
# Años con pocos países: muestra parcial y sesgada -> se avisa en el cuadro.
UMBRAL_COBERTURA_BAJA = 60
# Valores de referencia (años de vida saludable) para la leyenda de tamaño.
REF_TAMANO = [40, 60, 75]

# Conjunto curado de países que se etiquetan SIEMPRE (si están presentes),
# para poder seguir su evolución sin saturar el gráfico con ~140 etiquetas.
PAISES_ETIQUETADOS = [
    "United States", "Germany", "Japan", "Finland",
    "China", "India", "Brazil", "Russia", "Indonesia", "Mexico",
    "Nigeria", "Ethiopia", "Afghanistan", "Costa Rica",
]

# Desplazamiento de etiqueta por país (dx, dy en puntos) para separar pares
# que suelen quedar cerca; el resto usa el valor por defecto (6, 6).
OFFSET_ETIQUETA = {
    "China": (6, -15), "Indonesia": (6, 13), "Mexico": (6, 8),
    "Japan": (6, -13), "Germany": (6, 9), "Finland": (6, 8),
    "United States": (8, -3),
}

# Cuadros estáticos que se exportan como PNG de referencia.
# Se incluye 2005 porque ilustra la baja cobertura (aviso de muestra parcial).
ANIOS_FIGURA = [2005, 2006, 2010, 2015, 2020]


def cargar_limpio() -> pd.DataFrame:
    if not cfg.CLEANED_CSV.exists():
        import inspeccion_datos
        return inspeccion_datos.main()
    return pd.read_csv(cfg.CLEANED_CSV, encoding="utf-8")


def escala_tam(valores: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    """Mapea esperanza de vida saludable -> área de burbuja (escala fija)."""
    frac = (valores - vmin) / (vmax - vmin)
    return TAM_MIN + frac * (TAM_MAX - TAM_MIN)


def construir_plan(anios: list[int]) -> list[int]:
    """Secuencia de años a renderizar, con repetición para controlar el ritmo.

    Cada año real se repite ``FPS * SEGUNDOS_POR_ANIO`` cuadros (no se inventan
    datos intermedios: todos los cuadros de un año muestran EXACTAMENTE los
    datos de ese año). El primer y último año reciben una pausa extra.
    """
    por_anio = max(1, round(cfg.FPS * cfg.SEGUNDOS_POR_ANIO))
    pausa = max(0, round(cfg.FPS * cfg.PAUSA_INICIO_FIN))
    plan: list[int] = []
    for k, a in enumerate(anios):
        reps = por_anio + (pausa if k in (0, len(anios) - 1) else 0)
        plan += [a] * reps
    return plan


class Animador:
    """Crea la figura una vez y actualiza los artistas dinámicos por año."""

    def __init__(self, df: pd.DataFrame):
        regiones.validar_cobertura(df[cfg.COL_PAIS].unique())
        self.df = df.copy()
        self.df["__region"] = self.df[cfg.COL_PAIS].map(regiones.PAIS_A_REGION)
        self.df["__color"] = self.df["__region"].map(regiones.COLOR_REGION)

        self.anios = sorted(self.df[cfg.COL_ANIO].unique())
        self.xlim = (self.df[cfg.COL_X].min() - PAD_X,
                     self.df[cfg.COL_X].max() + PAD_X)
        self.ylim = (self.df[cfg.COL_Y].min() - PAD_Y,
                     self.df[cfg.COL_Y].max() + PAD_Y)
        self.tam_vmin = self.df[cfg.COL_TAM].min()
        self.tam_vmax = self.df[cfg.COL_TAM].max()

        # Datos por año y trayectorias de los países etiquetados.
        self.por_anio = {a: g for a, g in self.df.groupby(cfg.COL_ANIO)}
        self.etiquetados = [p for p in PAISES_ETIQUETADOS
                            if p in set(self.df[cfg.COL_PAIS])]
        self.trayectorias = {
            p: self.df[self.df[cfg.COL_PAIS] == p].sort_values(cfg.COL_ANIO)
            for p in self.etiquetados
        }

        self.fig = self.ax = None

    # --- construcción única de la figura ----------------------------------
    def crear_figura(self):
        self.fig, self.ax = plt.subplots(figsize=cfg.FIGSIZE)
        self.fig.subplots_adjust(left=0.07, right=0.985, top=0.84, bottom=0.13)
        ax = self.ax

        # Marca de agua con el año (detrás de todo).
        self.year_text = ax.text(
            0.5, 0.5, "", transform=ax.transAxes, ha="center", va="center",
            fontsize=170, fontweight="bold", color="#9aa7b4", alpha=0.13, zorder=0)

        # Estelas (una línea por país etiquetado).
        self.trail_lines = {}
        for p in self.etiquetados:
            col = regiones.COLOR_REGION[regiones.PAIS_A_REGION[p]]
            (ln,) = ax.plot([], [], color=col, alpha=0.28, lw=1.1, zorder=1)
            self.trail_lines[p] = ln

        # Burbujas (colección única, se actualiza cada cuadro).
        # IMPORTANTE: se inicializa con datos REALES del primer año. Un scatter
        # creado vacío (ax.scatter([], [])) no renderiza las caras de las
        # burbujas al guardar con FuncAnimation/FFMpegWriter (sí al usar
        # savefig), por lo que el video saldría sin burbujas.
        g0 = self.por_anio[self.anios[0]]
        self.scatter = ax.scatter(
            g0[cfg.COL_X].to_numpy(), g0[cfg.COL_Y].to_numpy(),
            s=escala_tam(g0[cfg.COL_TAM].to_numpy(), self.tam_vmin, self.tam_vmax),
            c=[to_rgba(c, ALPHA_BURBUJA) for c in g0["__color"]],
            edgecolors="white", linewidths=0.6, zorder=3)

        # Etiquetas (una anotación por país etiquetado), con halo blanco.
        self.labels = {}
        for p in self.etiquetados:
            ann = ax.annotate(
                p, (0, 0), xytext=OFFSET_ETIQUETA.get(p, (6, 6)),
                textcoords="offset points",
                fontsize=9, fontweight="bold", color="#111111", zorder=5,
                path_effects=[pe.withStroke(linewidth=2.6, foreground="white")])
            ann.set_visible(False)
            self.labels[p] = ann

        # Conteo de países (abajo a la izquierda, zona vacía del gráfico).
        self.n_text = ax.text(
            0.015, 0.03, "", transform=ax.transAxes, ha="left", va="bottom",
            fontsize=10, color="#555555",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#cccccc",
                      alpha=0.85), zorder=6)

        # Aviso de cobertura baja (visible solo en años con pocos países).
        self.warn_text = ax.text(
            0.5, 0.965, "", transform=ax.transAxes, ha="center", va="top",
            fontsize=10.5, fontweight="bold", color="#b00020", zorder=6,
            bbox=dict(boxstyle="round,pad=0.4", fc="#fff4f4", ec="#b00020",
                      alpha=0.92))
        self.warn_text.set_visible(False)

        # Ejes, rejilla y límites (constantes).
        ax.set_xlim(*self.xlim)
        ax.set_ylim(*self.ylim)
        ax.set_xlabel("Log del PIB per cápita  (log natural · ingreso →)",
                      fontsize=12, labelpad=8)
        ax.set_ylabel("Life Ladder — escalera de la vida, 0–10  (bienestar →)",
                      fontsize=12, labelpad=8)
        ax.grid(True, ls="--", lw=0.5, alpha=0.4)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=10)

        # Leyenda de color (regiones), arriba a la izquierda.
        handles_color = [
            Line2D([0], [0], marker="o", color="w", label=r,
                   markerfacecolor=regiones.COLOR_REGION[r], markersize=11,
                   markeredgecolor="white")
            for r in regiones.REGIONES
        ]
        leg_color = ax.legend(handles=handles_color, loc="upper left",
                              fontsize=9.5, title="Región (color)",
                              title_fontsize=10, framealpha=0.9, borderpad=0.8)
        ax.add_artist(leg_color)  # conservar al añadir la segunda leyenda

        # Leyenda de tamaño (esperanza de vida), abajo a la derecha (zona vacía).
        # markersize = sqrt(área) para que coincida con la escala del scatter.
        handles_tam = [
            Line2D([0], [0], marker="o", color="w",
                   label=f"{v} años",
                   markerfacecolor="#9aa7b4", markeredgecolor="white",
                   markersize=escala_tam(np.array([v]), self.tam_vmin,
                                         self.tam_vmax)[0] ** 0.5)
            for v in REF_TAMANO
        ]
        ax.legend(handles=handles_tam, loc="lower right",
                  title="Tamaño = esperanza de vida\nsaludable (años) · no población",
                  title_fontsize=8.5, fontsize=8.5, framealpha=0.9,
                  labelspacing=1.7, handletextpad=1.3, borderpad=1.0)

        # Títulos.
        self.fig.suptitle(
            "¿El ingreso de los países va acompañado de mayor bienestar?",
            fontsize=16.5, fontweight="bold", y=0.985)
        self.fig.text(
            0.5, 0.932,
            "Cada burbuja es un país · tamaño = esperanza de vida saludable al "
            "nacer (no población) · un año por paso",
            ha="center", fontsize=10.5, color="#444444")
        # Pie (2 líneas): encuadre transversal vs. intrapaís + fuente/advertencia.
        self.fig.text(
            0.5, 0.032,
            "Cada año compara países ENTRE sí (corte transversal); la cola de "
            "cometa de los países rotulados muestra su evolución EN EL TIEMPO.",
            ha="center", fontsize=8.5, color="#555555")
        self.fig.text(
            0.5, 0.009,
            "Fuente: World Happiness Report (2005–2020)  ·  Región = apoyo visual, "
            "no es variable de la base  ·  Se describen asociaciones, no causalidad.",
            ha="center", fontsize=8, color="#777777")
        return self.fig, self.ax

    # --- actualización por año --------------------------------------------
    def actualizar(self, anio: int):
        g = self.por_anio[anio]

        # Burbujas.
        self.scatter.set_offsets(np.column_stack(
            [g[cfg.COL_X].to_numpy(), g[cfg.COL_Y].to_numpy()]))
        self.scatter.set_sizes(
            escala_tam(g[cfg.COL_TAM].to_numpy(), self.tam_vmin, self.tam_vmax))
        self.scatter.set_facecolors(
            [to_rgba(c, ALPHA_BURBUJA) for c in g["__color"]])

        # Año y conteo.
        self.year_text.set_text(str(anio))
        self.n_text.set_text(f"n = {len(g)} países con datos completos")

        # Aviso de muestra parcial/sesgada en años de baja cobertura.
        if len(g) < UMBRAL_COBERTURA_BAJA:
            self.warn_text.set_text(
                f"Muestra parcial ({len(g)} países, sesgada a ingreso alto): "
                "no comparable con otros años")
            self.warn_text.set_visible(True)
        else:
            self.warn_text.set_visible(False)

        # Estelas y etiquetas.
        presentes = g.set_index(cfg.COL_PAIS)
        for p in self.etiquetados:
            presente = p in presentes.index
            tr = self.trayectorias[p]
            prev = tr[(tr[cfg.COL_ANIO] <= anio) &
                      (tr[cfg.COL_ANIO] >= anio - VENTANA_ESTELA)]
            # La estela se dibuja SOLO si el país tiene burbuja este año, para
            # no dejar "colas huérfanas" que apunten a la nada (p. ej. un país
            # fuera del conteo "n =" del cuadro).
            if presente and len(prev) >= 2:
                self.trail_lines[p].set_data(prev[cfg.COL_X], prev[cfg.COL_Y])
            else:
                self.trail_lines[p].set_data([], [])

            if presente:
                fila = presentes.loc[p]
                self.labels[p].xy = (fila[cfg.COL_X], fila[cfg.COL_Y])
                self.labels[p].set_visible(True)
            else:
                self.labels[p].set_visible(False)

        artistas = [self.scatter, self.year_text, self.n_text, self.warn_text,
                    *self.trail_lines.values(), *self.labels.values()]
        return artistas


def generar_video(anim: Animador) -> None:
    anim.crear_figura()
    plan = construir_plan(anim.anios)

    def update(i):
        return anim.actualizar(plan[i])

    print(f"Render: {len(plan)} cuadros ({len(anim.anios)} años, "
          f"{cfg.FPS} fps) -> {cfg.VIDEO_OUT.name}")
    animation = FuncAnimation(anim.fig, update, frames=len(plan), blit=False)
    writer = FFMpegWriter(
        fps=cfg.FPS, bitrate=4000,
        metadata={"title": "World Happiness - ingreso y bienestar",
                  "comment": "Asociacion, no causalidad"})
    animation.save(str(cfg.VIDEO_OUT), writer=writer, dpi=cfg.DPI)
    plt.close(anim.fig)
    print(f"Video guardado: {cfg.VIDEO_OUT}")


def exportar_cuadros(anim: Animador) -> None:
    """Exporta PNGs estáticos de años de referencia a output/figures/."""
    anim.crear_figura()
    for a in ANIOS_FIGURA:
        if a not in anim.anios:
            continue
        anim.actualizar(a)
        out = cfg.FIGURES_DIR / f"frame_{a}.png"
        anim.fig.savefig(out, dpi=110)
        print(f"Cuadro estático: {out}")
    plt.close(anim.fig)


def main() -> None:
    cfg.asegurar_directorios()
    df = cargar_limpio()
    exportar_cuadros(Animador(df))
    generar_video(Animador(df))


if __name__ == "__main__":
    main()
