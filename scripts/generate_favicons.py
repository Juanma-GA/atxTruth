"""Generate square favicons from the ALTEN logo (symbol only, without the "ALTEN" wordmark).

Usage (from the repository root, with the backend's Python, which has Pillow in the dev lockfile):
    backend/.venv/bin/python scripts/generate_favicons.py        (Windows: backend\\.venv\\Scripts\\python)

Reads sources/design/alten_logo.png (never modified) and writes into frontend/public/:
favicon.ico (16 + 32), favicon-32.png, apple-touch-icon.png (180) and icon-512.png.
The symbol keeps its proportions, is centred and gets a transparent margin.
"""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources" / "design" / "alten_logo.png"
OUT = ROOT / "frontend" / "public"
# Share of the square left as transparent margin on each side (small icons need the room to stay legible).
MARGIN = 0.06


def symbol(logo: Image.Image) -> Image.Image:
    """Crop to the symbol: the opaque rows above the first fully transparent gap (the wordmark is below)."""
    alpha = logo.getchannel("A")
    width, height = logo.size
    for y in range(height):
        if alpha.crop((0, y, width, y + 1)).getbbox() is None:
            cropped = logo.crop((0, 0, width, y))
            box = cropped.getbbox()
            if box is None:
                raise SystemExit("The logo has no opaque pixels above the gap.")
            return cropped.crop(box)
    raise SystemExit("No transparent gap between symbol and wordmark: the logo layout changed.")


def square(icon: Image.Image, size: int) -> Image.Image:
    inner = size * (1 - 2 * MARGIN)
    scale = min(inner / icon.width, inner / icon.height)
    resized = icon.resize((max(1, round(icon.width * scale)), max(1, round(icon.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(resized, ((size - resized.width) // 2, (size - resized.height) // 2), resized)
    return canvas


def main() -> int:
    logo = Image.open(SOURCE).convert("RGBA")
    mark = symbol(logo)
    OUT.mkdir(parents=True, exist_ok=True)
    square(mark, 32).save(OUT / "favicon-32.png", optimize=True)
    square(mark, 180).save(OUT / "apple-touch-icon.png", optimize=True)
    square(mark, 512).save(OUT / "icon-512.png", optimize=True)
    # Each ICO frame is drawn at its own size (not downscaled from 32), so 16 px stays sharp.
    frames = [square(mark, 16), square(mark, 32)]
    frames[1].save(OUT / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32)], append_images=[frames[0]])
    stale = OUT / "favicon.png"
    if stale.exists():
        stale.unlink()
    print(f"Symbol {mark.size[0]}x{mark.size[1]} px → favicons written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
