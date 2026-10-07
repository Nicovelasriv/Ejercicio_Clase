"""
Orquestador del proyecto: ejecuta TODO el pipeline desde cero.

Pasos:
  1. Descarga la base si falta.
  2. Inspecciona y limpia los datos (-> datos_limpios_animacion.csv).
  3. Calcula el análisis descriptivo (-> resumen_datos.csv).
  4. Genera los gráficos estáticos de apoyo (-> output/figures/).
  5. Produce la animación (-> output/video_final.mp4) y cuadros de referencia.
  6. Verifica el video resultante.

Uso:
    python3 src/run_all.py
"""

from __future__ import annotations

import time

import config as cfg
import inspeccion_datos
import graficos
import animacion
import verificar_video


def main() -> None:
    t0 = time.time()
    print("\n########## 1/5  Descarga + inspección + limpieza ##########")
    cfg.descargar_si_falta()
    df = inspeccion_datos.main()

    print("\n########## 2/5  Análisis + resumen_datos.csv + gráficos ##########")
    graficos.main()  # ejecuta el análisis y guarda resumen_datos.csv y figuras

    print("\n########## 3/5  Cuadros estáticos de referencia ##########")
    animacion.exportar_cuadros(animacion.Animador(df))

    print("\n########## 4/5  Render de la animación (video_final.mp4) ##########")
    animacion.generar_video(animacion.Animador(df))

    print("\n########## 5/5  Verificación del video ##########")
    ok = verificar_video.verificar()

    print(f"\nPipeline completo en {time.time() - t0:.1f}s. "
          f"Video {'OK' if ok else 'CON PROBLEMAS'}: {cfg.VIDEO_OUT}")


if __name__ == "__main__":
    main()
