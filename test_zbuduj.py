"""Testy generatora pakietu. Uruchomienie: python3 -m unittest -v"""
import pathlib
import re
import shutil
import tempfile
import unittest

import zbuduj

HERE = pathlib.Path(__file__).resolve().parent


class EncodeTest(unittest.TestCase):
    def test_bit_order_lsb_first_and_black_is_one(self):
        image = [[False] * 16 for _ in range(2)]
        image[0][0] = True   # lewy piksel -> najmłodszy bit
        image[0][9] = True   # drugi bajt, bit 1
        image[1][7] = True   # najstarszy bit
        self.assertEqual(zbuduj.encode_bm(image), bytes([0x00, 0x01, 0x02, 0x80, 0x00]))

    def test_round_trip(self):
        portrait = zbuduj.load_portrait(HERE / "papiez.txt")
        for frame in zbuduj.make_frames(portrait):
            data = zbuduj.encode_bm(frame)
            self.assertEqual(zbuduj.decode_bm(data, 128, 64), frame)

    def test_frame_size_within_firmware_limit(self):
        # animation_storage.c: rozmiar pliku <= ROUND_UP(width, 8) * height + 1
        frame = [[False] * 128 for _ in range(64)]
        self.assertEqual(len(zbuduj.encode_bm(frame)), 16 * 64 + 1)


class PortraitTest(unittest.TestCase):
    def test_portrait_shape(self):
        portrait = zbuduj.load_portrait(HERE / "papiez.txt")
        self.assertEqual(len(portrait), 64)
        self.assertEqual({len(r) for r in portrait}, {52})
        # pierwszy i ostatni wiersz puste - przesunięcie o 1 px niczego nie ucina
        self.assertFalse(any(portrait[0]))
        self.assertFalse(any(portrait[-1]))

    def test_frames_keep_every_pixel(self):
        portrait = zbuduj.load_portrait(HERE / "papiez.txt")
        black = sum(map(sum, portrait))
        for frame in zbuduj.make_frames(portrait):
            self.assertEqual(sum(map(sum, frame)), black)

    def test_rejects_bad_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "zly.txt"
            path.write_text("##.\n#x.\n")
            with self.assertRaises(ValueError):
                zbuduj.load_portrait(path)

    def test_compose_clips_outside_screen(self):
        screen = zbuduj.compose([[True, True]], 127, 63)
        self.assertTrue(screen[63][127])
        self.assertEqual(sum(map(sum, screen)), 1)


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        shutil.copy(HERE / "papiez.txt", self.tmp / "papiez.txt")
        self.anim_dir = zbuduj.build(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def fields(self, path):
        return dict(re.findall(r"^([A-Za-z ]+): (.*)$", path.read_text(), re.M))

    def test_layout(self):
        anims = self.tmp / "asset_packs" / "Papiez" / "Anims"
        self.assertEqual(self.anim_dir, anims / "Papiez_128x64")
        manifest = self.fields(anims / "manifest.txt")
        self.assertEqual(manifest["Filetype"], "Flipper Animation Manifest")
        self.assertEqual(manifest["Name"], "Papiez_128x64")
        self.assertTrue((self.tmp / "podglad.png").read_bytes().startswith(b"\x89PNG"))

    def test_meta_consistent_with_frames(self):
        meta = self.fields(self.anim_dir / "meta.txt")
        self.assertEqual(meta["Filetype"], "Flipper Animation")
        passive, active = int(meta["Passive frames"]), int(meta["Active frames"])
        order = [int(x) for x in meta["Frames order"].split()]
        # Wymagania parsera Momentum: liczba wpisów = passive + active,
        # klatki numerowane od 0 bez dziur, każda istnieje jako frame_N.bm
        self.assertEqual(len(order), passive + active)
        self.assertEqual(sorted(set(order)), list(range(max(order) + 1)))
        files = sorted(p.name for p in self.anim_dir.glob("frame_*.bm"))
        self.assertEqual(files, [f"frame_{i}.bm" for i in range(max(order) + 1)])
        for name in files:
            self.assertLessEqual((self.anim_dir / name).stat().st_size, 16 * 64 + 1)

    def test_bubble_covers_whole_active_phase(self):
        meta = self.fields(self.anim_dir / "meta.txt")
        passive, active = int(meta["Passive frames"]), int(meta["Active frames"])
        cycles = int(meta["Active cycles"])
        self.assertEqual(int(meta["StartFrame"]), passive)
        self.assertEqual(int(meta["EndFrame"]), passive + active * cycles - 1)
        self.assertEqual(int(meta["Bubble slots"]), 1)
        # tylko ASCII - fonty Flippera nie mają polskich znaków
        self.assertTrue(meta["Text"].isascii())


if __name__ == "__main__":
    unittest.main()
