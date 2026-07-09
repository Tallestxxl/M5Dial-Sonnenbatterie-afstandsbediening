# Sonnen Dial hardware checklist

Praktische koop- en bring-up-checklist voor de stand-alone M5 Dial afstandsbediening.

## Kopen

Koop de **M5Stack Dial**, ook aangeduid als **Dial SKU K130** of **M5Dial**. Niet verwarren met losse M5StampS3-modules, Atom/Stick-apparaten of andere ronde M5-producten: deze firmware gebruikt de ingebouwde rotary encoder, het ronde 240x240 touch-display, de screen button en de M5Dial power wrapper.

Minimale set:

- 1x M5Stack Dial / M5Dial / SKU K130.
- USB-C datakabel, niet alleen laadkabel.
- Optioneel: 3.7V LiPo met passende 1.25mm 2-pin connector als hij echt los van USB/vaste voeding moet werken.
- Optioneel: 6-36V DC voeding op de rear terminal als hij aan de muur permanent gevoed wordt.

Let bij bestellen op:

- Productnaam bevat `Dial` of `M5Dial`.
- SKU is `K130`.
- Board heeft ESP32-S3 / M5StampS3.
- Het apparaat heeft een 1.28 inch rond TFT touch-display en rotary encoder.
- Er staat een batterijconnector of rear power terminal vermeld als je hem stand-alone wilt gebruiken.

M5Stack noemt op de distributeurspagina voor Nederland onder andere Elektor en TinyTronics. De officiële shop, Mouser en Digi-Key zijn ook genoemd als algemene kanalen. Controleer actuele prijs, voorraad en levertijd direct bij de winkel voordat je bestelt.

## Eerste test na ontvangst

1. Sluit de M5 Dial met een echte USB-C datakabel aan.
2. Controleer of hij zichtbaar wordt als seriële poort:

```sh
scripts/sonnen-dial ports
```

3. Installeer de libraries in de workspace:

```sh
scripts/sonnen-dial libs
```

4. Compileer eerst zonder echte Sonnen-config:

```sh
scripts/sonnen-dial check
scripts/sonnen-dial compile
```

5. Maak voor een pure hardware/UI-test eventueel een demo-config:

```sh
scripts/sonnen-probe make-config --force --demo --wifi-ssid DEMO --wifi-password DEMO --host 192.168.1.50 --dim-after-ms 120000 --sleep-after-ms 0
```

Met `--sleep-after-ms 0` schakelt de demo niet automatisch helemaal uit. `SONNEN_ENABLE_POWER_OFF` blijft standaard `0`, waardoor ook de handmatige slaapactie voorlopig alleen dimt. Dat is veiliger tijdens de eerste hardwaretest, omdat dimmen eenvoudig met draaien of drukken terugkomt.

6. Upload met `scripts/sonnen-dial upload PORT`, en controleer scherm, encoder, knop en dimmen.
7. Test daarna de echte Wi-Fi/HTTP-flow zonder batterij door op de laptop een mockserver te starten:

```sh
scripts/sonnen-mock --host 0.0.0.0 --port 8766
```

Maak in een tweede terminal een mock-config met het IP-adres van je laptop op hetzelfde Wi-Fi-netwerk:

```sh
scripts/sonnen-probe make-config --force --wifi-ssid YOUR_WIFI --wifi-password YOUR_PASSWORD --host LAPTOP_IP --port 8766
```

Upload en test `STATUS` op de M5 Dial. De waarden komen dan van de mockserver, niet van de echte Sonnenbatterie.

8. Maak daarna een echte read-only config. Deze laat `SONNEN_ALLOW_WRITES` standaard op `0`:

```sh
scripts/sonnen-probe make-config --force --wifi-ssid YOUR_WIFI --wifi-password YOUR_PASSWORD --host 192.168.1.50 --token YOUR_TOKEN
```

9. Laat `SONNEN_ALLOW_WRITES` eerst op `0`.
10. Probe eerst vanaf de laptop of de status-API klopt:

```sh
scripts/sonnen-probe status --host 192.168.1.50 --token YOUR_TOKEN
```

11. Upload met de gevonden poort.
12. Test eerst alleen `STATUS` op de M5 Dial.
13. Zet `SONNEN_ALLOW_WRITES` pas op `1` nadat de laptop-probe en de M5-status betrouwbaar werken en je zeker weet dat de write-paden/modes kloppen voor jouw batterij.
14. Test daarna pas `SELF`, `CHARGE` en `DISCH`.

## Sonnen veiligheid

Gebruik de eerste echte test met een lage limiet, bijvoorbeeld `SONNEN_MAX_SETPOINT_W 500`. Verhoog pas als duidelijk is dat jouw sonnenBatterie de geconfigureerde API-paden en operating modes precies zo interpreteert als verwacht.

Standaard is `SONNEN_ALLOW_WRITES` daarom `0`: de remote kan status lezen, maar geen modus of setpoint wijzigen. Dat maakt de eerste upload veel minder spannend.

Standaard is `SONNEN_DEMO_MODE` `0`. Zet hem alleen tijdelijk op `1` om de M5 Dial zelf te testen zonder netwerk. In demo-modus worden schrijfacties nooit verstuurd.

Standaard is `SONNEN_WIFI_OFF_AFTER_REQUEST` `1`: na elke API-call wordt Wi-Fi uitgezet. Dat maakt statusverversen iets trager, maar past beter bij een compacte batterijgevoede afstandsbediening.

Voor een huiskamer-afstandsbediening is het beste gedrag:

- Lezen mag automatisch.
- Schrijven alleen na expliciete knopbevestiging.
- Charge/discharge-setpoints zijn begrensd.
- Lange druk schakelt uit of annuleert.
- Self-consumption blijft altijd snel bereikbaar.

Voor endpoint-checks vanaf de laptop is er `scripts/sonnen-probe`. Een niet-GET request wordt geweigerd tenzij je bewust `--allow-write --confirm-write YES` meegeeft. Gebruik dat alleen met een lage setpoint-limiet en pas nadat je de endpoint-documentatie of response van jouw batterij hebt gecontroleerd.

Voor Wi-Fi/HTTP-tests zonder echte batterij is er `scripts/sonnen-mock`. Die serveert `/api/v2/status` en weigert writes standaard met HTTP 423. Start de mock alleen met `--allow-writes` als je expliciet de firmware-write-flow tegen de mock wilt droogtesten.

## Bekende repo-notitie

Deze workspace heeft lokaal `arduino/` in `.git/info/exclude` staan. De firmwarebestanden bestaan gewoon op schijf, maar verschijnen niet standaard in `git status`. Als we ze later willen committen, gebruik dan bewust `git add -f arduino/...`.
