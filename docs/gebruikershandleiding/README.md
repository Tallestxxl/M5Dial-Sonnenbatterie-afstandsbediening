# Handleidingen

De gepubliceerde handleidingen staan hier:

- [Gebruikershandleiding v1.1](M5Dial-Sonnenbatterie-gebruikershandleiding-versie-1.1.pdf)
- [Installateurshandleiding v1.0](M5Dial-Sonnenbatterie-installateurshandleiding-versie-1.0.pdf)

Beide PDF's worden gegenereerd uit `build_manual.py`. De bron gebruikt de projectfoto's uit `docs/images/` en `hardware/case/` en bevat geen wifi-wachtwoorden, API-tokens of andere private configuratie.

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
docs/gebruikershandleiding/M5Dial-Sonnenbatterie-gebruikershandleiding-versie-1.1.pdf
docs/gebruikershandleiding/M5Dial-Sonnenbatterie-installateurshandleiding-versie-1.0.pdf
```

## Bij firmwarewijzigingen

Wijzigt zichtbaar gedrag, bediening, teksten, limieten, timing, netwerkgedrag, voeding, installatie of veiligheid, pas dan ook `build_manual.py` aan en voer `scripts/build-manual` uit. Commit de gewijzigde bron en beide PDF's samen met de firmware.

De GitHub Actions-controle bouwt beide PDF's opnieuw en controleert dat de vastgelegde versies actueel zijn. Als de firmware wijzigt zonder een wijziging aan de handleidingbron, meldt de workflow dat de documentatie niet aantoonbaar is beoordeeld. Verhoog bij een nieuwe gepubliceerde documentversie ook de bestandsnaam, het versienummer op de omslag en de links in deze README en de repository-README.
