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

# Pasek statusu Momentum rysuje u góry dwie "zakładki": ikony po lewej
# (do x=42) oraz zegar z baterią po prawej (od x=70), obie do y=12.
# Czubek głowy stoi w luce między nimi, prawa strona ekranu zostaje na dymki.
PORTRAIT_X = 28

# Teksty dymków. Po każdym naciśnięciu przycisku Momentum losuje jeden.
# "\n" łamie linię. Polskie znaki są zamieniane na łacińskie, bo font
# Flippera ich nie ma.
TEKSTY = [
    "Jeszcze\njak!",
    "Z warko-\nczykami\nczy bez?",
    "nie wiem",
    "Jest\nmożliwe",
    "Jak Pan\nJezus\npowiedział?",
    "Okrutnik!",
    "Tak Pan\nJezus\npowiedział",
    "A można,\njak\nnajbardziej.",
]

# Dymek staje na prawo od twarzy (x=83); szerszy przesuwa się w lewo tak,
# żeby nie wyjść za ekran. Pionowo: środek na wysokości oczu, ale nie
# wyżej niż pod paskiem statusu.
BUBBLE_X = 83
BUBBLE_CENTER_Y = 31
STATUS_BAR_BOTTOM = 13

# Font dymków (FontSecondary = haxrcorp4089): przesunięcie po każdym znaku
# i szerokość ostatniego znaku, dla ASCII 32..126 (jedna cyfra na znak).
# Wysokość linii 11 px, ramka dymka: tekst + 8 px szerokości, + 4 px wysokości.
_FONT_ADV = "22466872446636286366666666234646966666666266686666666668666484664555553552352855554445585554247"
_FONT_LAST = "21355761335525175255555555123535855555555155575555555557555373553444442441241744443334474443136"
FONT_LINE_H = 11

_PL = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def to_ascii(text):
    out = text.translate(_PL)
    if not all(32 <= ord(c) < 127 or c == "\n" for c in out):
        raise ValueError(f"znak spoza ASCII w tekście dymka: {text!r}")
    return out


def text_width(line):
    """Szerokość linii w pikselach, jak u8g2_GetStrWidth."""
    if not line:
        return 0
    adv = [int(_FONT_ADV[ord(c) - 32]) for c in line]
    return sum(adv[:-1]) + int(_FONT_LAST[ord(line[-1]) - 32])


def bubble_box(text):
    """(szerokość, wysokość) ramki dymka jak w elements_bubble_str."""
    lines = text.split("\n")
    return max(text_width(l) for l in lines) + 8, FONT_LINE_H * len(lines) + 4


def place_bubble(text):
    w, h = bubble_box(text)
    x = min(BUBBLE_X, SCREEN_W - w)
    y = max(STATUS_BAR_BOTTOM + 1, min(SCREEN_H - h, BUBBLE_CENTER_Y - h // 2))
    return x, y


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
PASSIVE_FRAMES, ACTIVE_FRAMES, ACTIVE_CYCLES = 2, 2, 4

META_HEAD = """\
Filetype: Flipper Animation
Version: 1

Width: {w}
Height: {h}
Passive frames: {passive}
Active frames: {active}
Frames order: 0 1 0 1
Active cycles: {cycles}
Frame rate: 2
Duration: 3600
Active cooldown: 3

Bubble slots: {slots}
"""

META_SLOT = """
Slot: {slot}
X: {x}
Y: {y}
Text: {text}
AlignH: Left
AlignV: Center
StartFrame: {start}
EndFrame: {end}
"""


def make_meta(texts=TEKSTY):
    meta = META_HEAD.format(w=SCREEN_W, h=SCREEN_H, passive=PASSIVE_FRAMES,
                            active=ACTIVE_FRAMES, cycles=ACTIVE_CYCLES, slots=len(texts))
    start = PASSIVE_FRAMES
    end = PASSIVE_FRAMES + ACTIVE_FRAMES * ACTIVE_CYCLES - 1
    for slot, raw in enumerate(texts):
        text = to_ascii(raw)
        x, y = place_bubble(text)
        meta += META_SLOT.format(slot=slot, x=x, y=y, text=text.replace("\n", "\\n"),
                                 start=start, end=end)
    return meta


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
    (anim_dir / "meta.txt").write_text(make_meta(), encoding="ascii")
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
