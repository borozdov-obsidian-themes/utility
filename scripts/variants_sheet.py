"""Render screenshots/variants.png: every Style Settings variant of this theme
as a split dark/light thumbnail with its name, for the README.

Usage: npm run variants:sheet   (after npm run variants; needs Obsidian, Chrome)
"""
import pathlib
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import screenshots  # noqa: E402

from variants_config import ID, DEFAULT_LABEL, MEMBERS  # noqa: E402

COLS, W, H, CAPTION = 4, 400, 225, 36


def main():
    entries = [("default", DEFAULT_LABEL)] + list(MEMBERS)
    rows = -(-len(entries) // COLS)
    sheet = Image.new("RGB", (COLS * W, rows * (H + CAPTION)), "#fff")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        screenshots.extract(screenshots.obsidian_asar(), {
            "app.css", "public/images/6155340132a851f6089e.svg", "public/images/2308ab1944a6bfa5c5b8.svg"}, tmp)
        (tmp / "theme.css").write_text((ROOT / "theme.css").read_text())
        for i, (slug, label) in enumerate(entries):
            halves = {}
            for face in ("dark", "light"):
                out = tmp / f"{slug}-{face}.png"
                screenshots.render(tmp, face, out, 1024, 576, platform=f"{screenshots.DESKTOP} {ID}-{slug}")
                halves[face] = Image.open(out).convert("RGB")
            split = halves["dark"].copy()
            w, h = split.size
            split.paste(halves["light"].crop((w // 2, 0, w, h)), (w // 2, 0))
            x, y = (i % COLS) * W, (i // COLS) * (H + CAPTION)
            sheet.paste(split.resize((W, H), Image.LANCZOS), (x, y))
            draw.text((x + 10, y + H + 8), label, fill="#222", font=font)
    sheet.save(ROOT / "screenshots" / "variants.png", optimize=True)
    print(f"wrote screenshots/variants.png: {len(entries)} variants")


if __name__ == "__main__":
    main()
