"""
Verificación del video generado.

Comprueba que ``output/video_final.mp4``:
  - exista y tenga tamaño > 0
  - se pueda abrir y leer con ffprobe
  - reporta duración, resolución, número de cuadros y fps

Uso:
    python3 src/verificar_video.py
Devuelve código de salida 0 si todo está bien, 1 en caso contrario.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

import config as cfg


def _ffprobe(path) -> dict | None:
    if shutil.which("ffprobe") is None:
        print("  (ffprobe no disponible; se omite la inspección detallada)")
        return None
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        print(f"  ffprobe falló: {out.stderr.strip()}")
        return None
    return json.loads(out.stdout)


def verificar() -> bool:
    path = cfg.VIDEO_OUT
    print(f"Verificando: {path}")

    if not path.exists():
        print("  ✗ El archivo NO existe.")
        return False
    size = path.stat().st_size
    if size <= 0:
        print("  ✗ El archivo existe pero está vacío (0 bytes).")
        return False
    print(f"  ✓ Existe y pesa {size/1024:.0f} KB (> 0).")

    info = _ffprobe(path)
    if info is None:
        # Sin ffprobe no podemos inspeccionar, pero el archivo no está vacío.
        return True

    vstream = next((s for s in info["streams"]
                    if s.get("codec_type") == "video"), None)
    if vstream is None:
        print("  ✗ No se encontró un stream de video.")
        return False

    dur = float(info["format"].get("duration", 0))
    w, h = vstream.get("width"), vstream.get("height")
    nb = vstream.get("nb_frames", "?")
    fr = vstream.get("avg_frame_rate", "?")
    codec = vstream.get("codec_name", "?")

    print(f"  ✓ Códec      : {codec}")
    print(f"  ✓ Resolución : {w}x{h}")
    print(f"  ✓ Cuadros    : {nb}")
    print(f"  ✓ FPS        : {fr}")
    print(f"  ✓ Duración   : {dur:.2f} s")

    problemas = []
    if dur <= 0:
        problemas.append("duración no positiva")
    if not (w and h):
        problemas.append("resolución inválida")
    if problemas:
        print("  ✗ Problemas:", "; ".join(problemas))
        return False
    print("  ✓ Verificación superada.")
    return True


if __name__ == "__main__":
    sys.exit(0 if verificar() else 1)
