"""Buduje pakiet zasobów "Papiez" dla firmware Momentum na Flipper Zero.

Użycie: python3 zbuduj.py

Wejście:  papiez.txt - portret 52x64, "#" = czarny piksel, "." = tło.
Wyjście:  asset_packs/Papiez/Anims/...   - do skopiowania na kartę SD
          podglad.png                     - podgląd klatek (skala 4x)

Bez zależności - tylko biblioteka standardowa Pythona.
"""
import pathlib
import struct
import zlib

HERE = pathlib.Path(__file__).resolve().parent

PACK_NAME = "Papiez"
ANIM_NAME = "Papiez_128x64"
SCREEN_W, SCREEN_H = 128, 64

# Papież lekko na prawo od środka: górne rogi ekranu zajmują ikony paska
# statusu (po lewej) i bateria (po prawej), lewa strona zostaje na dymek.
PORTRAIT_X = 44

MANIFEST = """\
Filetype: Flipper Animation Manifest
Version: 1

Name: {name}
Min butthurt: 0
Max butthurt: 14
Min level: 1
Max level: 30
Weight: 3
"""

# 2 klatki pasywne (lekkie kiwanie głową). Po naciśnięciu przycisku:
# te same 2 klatki x 4 cykle z dymkiem. Numery klatek dymka liczone są
# od początku: pasywne 0-1, aktywne 2-9.
META = """\
Filetype: Flipper Animation
Version: 1

Width: {w}
Height: {h}
Passive frames: 2
Active frames: 2
Frames order: 0 1 0 1
Active cycles: 4
Frame rate: 2
Duration: 3600
Active cooldown: 3

Bubble slots: 1

Slot: 0
X: 1
Y: 20
Text: Szczesc\\nBoze!
AlignH: Right
AlignV: Center
StartFrame: 2
EndFrame: 9
"""


def load_portrait(path):
    rows = path.read_text(encoding="utf-8").split()
    width = len(rows[0])
    for row in rows:
        if len(row) != width or set(row) - {"#", "."}:
            raise ValueError(f"{path}: wiersze muszą mieć równą długość i tylko znaki # .")
    return [[c == "#" for c in row] for row in rows]


def compose(portrait, x0, y0):
    """Ekran 128x64 z portretem w (x0, y0); piksele poza ekranem są obcinane."""
    screen = [[False] * SCREEN_W for _ in range(SCREEN_H)]
    for y, row in enumerate(portrait):
        for x, black in enumerate(row):
            sx, sy = x0 + x, y0 + y
            if black and 0 <= sx < SCREEN_W and 0 <= sy < SCREEN_H:
                screen[sy][sx] = True
    return screen


def make_frames(portrait):
    # Klatka 1 przesunięta o 1 piksel w dół - pierwszy i ostatni wiersz
    # portretu są puste, więc nic nie ginie.
    return [compose(portrait, PORTRAIT_X, 0), compose(portrait, PORTRAIT_X, 1)]


def encode_bm(image):
    """Format .bm Flippera bez kompresji: bajt 0x00 i bity XBM
    (wiersz po wierszu, najmłodszy bit = lewy piksel, 1 = czarny)."""
    out = bytearray([0x00])
    for row in image:
        for bx in range(0, len(row), 8):
            byte = 0
            for bit, black in enumerate(row[bx:bx + 8]):
                if black:
                    byte |= 1 << bit
            out.append(byte)
    return bytes(out)


def decode_bm(data, width, height):
    """Odwrotność encode_bm (do testów)."""
    if data[0] != 0x00:
        raise ValueError("obsługiwany jest tylko format bez kompresji")
    stride = (width + 7) // 8
    return [
        [bool(data[1 + y * stride + x // 8] >> (x % 8) & 1) for x in range(width)]
        for y in range(height)
    ]


def write_png(path, image, scale, fg=(0, 0, 0), bg=(255, 140, 0)):
    height, width = len(image), len(image[0])
    raw = bytearray()
    for row in image:
        line = bytearray()
        for black in row:
            line += bytes(fg if black else bg) * scale
        for _ in range(scale):
            raw += b"\x00" + line

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(
            ">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width * scale, height * scale, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def build(root=HERE):
    portrait = load_portrait(root / "papiez.txt")
    frames = make_frames(portrait)

    anims = root / "asset_packs" / PACK_NAME / "Anims"
    anim_dir = anims / ANIM_NAME
    anim_dir.mkdir(parents=True, exist_ok=True)
    (anims / "manifest.txt").write_text(MANIFEST.format(name=ANIM_NAME), encoding="ascii")
    (anim_dir / "meta.txt").write_text(META.format(w=SCREEN_W, h=SCREEN_H), encoding="ascii")
    for i, frame in enumerate(frames):
        (anim_dir / f"frame_{i}.bm").write_bytes(encode_bm(frame))

    # Podgląd: obie klatki obok siebie, oddzielone pionową kreską.
    gap = [[True] for _ in range(SCREEN_H)]
    side_by_side = [frames[0][y] + gap[y] + frames[1][y] for y in range(SCREEN_H)]
    write_png(root / "podglad.png", side_by_side, scale=4)
    return anim_dir


if __name__ == "__main__":
    out = build()
    print(f"Gotowe: {out.parent.parent}")
