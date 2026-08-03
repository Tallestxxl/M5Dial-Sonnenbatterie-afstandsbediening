# Gebruikershandleiding

De actuele handleiding staat hier:

[M5Dial-Sonnenbatterie-gebruikershandleiding-actueel.pdf](M5Dial-Sonnenbatterie-gebruikershandleiding-actueel.pdf)

De PDF wordt gegenereerd uit `build_manual.py`. De bron gebruikt de projectfoto's uit `docs/images/` en `hardware/case/` en bevat geen wifi-wachtwoorden, API-tokens of andere private configuratie.

## Opnieuw bouwen

Installeer de Python-pakketten:

```sh
python3 -m pip install -r docs/gebruikershandleiding/requirements.txt
```

Bouw de PDF vanaf de repository-root:

```sh
scripts/build-manual
```

De generator schrijft rechtstreeks naar:

```text
docs/gebruikershandleiding/M5Dial-Sonnenbatterie-gebruikershandleiding-actueel.pdf
```

## Bij firmwarewijzigingen

Wijzigt zichtbaar gedrag, bediening, teksten, limieten, timing, netwerkgedrag, voeding of veiligheid, pas dan ook `build_manual.py` aan en voer `scripts/build-manual` uit. Commit de gewijzigde bron en PDF samen met de firmware.

De GitHub Actions-controle bouwt de PDF opnieuw en controleert dat de vastgelegde PDF actueel is. Als de firmware wijzigt zonder een wijziging aan de handleidingbron, meldt de workflow dat de documentatie niet aantoonbaar is beoordeeld.
