# Papież na Flipperze

Pakiet zasobów (asset pack) dla firmware **Momentum** na Flipper Zero: zamiast
delfina na pulpicie pojawia się portret papieża. Po naciśnięciu dowolnego
przycisku na pulpicie papież mówi „Szczesc Boze!”.

![Podgląd klatek animacji](podglad.png)

*Obie klatki animacji (skala 4x). Papież lekko kiwa głową.*

## Instalacja

1. Skopiuj folder `asset_packs/Papiez` na kartę microSD Flippera do
   `/ext/asset_packs/` (np. przez qFlipper: zakładka plików, SD Card,
   `asset_packs`). Docelowo ma powstać `/ext/asset_packs/Papiez/Anims/manifest.txt`.
2. Na Flipperze otwórz aplikację **Momentum** i przejdź do
   **Interface → Graphics → Asset Pack**. Wybierz **Papiez**.
3. Wyjdź z ustawień. Jeśli Flipper poprosi o restart, zgódź się.

Żeby wrócić do delfina, ustaw w tym samym miejscu Asset Pack na **Default**.

## Uwagi

- Animacja zajmuje cały ekran 128x64, a papież stoi lekko na prawo od środka.
  Ikony paska statusu (lewy górny róg) i bateria (prawy górny róg) nie zasłaniają
  głowy. Jeśli w ustawieniach Momentum włączysz tło paska statusu na całą
  szerokość, zakryje ono czubek głowy.
- Fonty Flippera nie mają polskich znaków, dlatego dymek mówi „Szczesc Boze!”.
- Pakiet działa tylko na firmware Momentum. Oficjalne firmware nie obsługuje
  pakietów zasobów.

## Budowanie

Gotowy pakiet leży w `asset_packs/`. Po zmianie portretu albo tekstów zbuduj go
ponownie (wystarczy Python 3, bez dodatkowych bibliotek):

```sh
python3 zbuduj.py
```

Skrypt tworzy `asset_packs/Papiez` i odświeża `podglad.png`.

### Zmiana portretu

Portret leży w `papiez.txt`: 64 wiersze po 52 znaki, `#` to czarny piksel,
`.` to tło. Pierwszy i ostatni wiersz muszą zostać puste, bo druga klatka jest
przesunięta o 1 piksel w dół.

Tekst dymka, położenie papieża i tempo animacji ustawisz na początku `zbuduj.py`.

## Testy

```sh
python3 -m unittest -v
```

Testy sprawdzają format plików `.bm` (kolejność bitów, rozmiar w limicie
firmware) i zgodność `meta.txt` z klatkami według reguł parsera Momentum.

## Licencja

MIT - szczegóły w pliku [LICENSE](LICENSE).
