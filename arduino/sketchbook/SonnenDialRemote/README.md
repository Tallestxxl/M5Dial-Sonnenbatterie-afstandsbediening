# SonnenDialRemote

Stand-alone M5Stack Dial afstandsbediening voor een sonnenBatterie op het lokale netwerk.

Hardware eerst kopen? Zie [docs/sonnen-dial-hardware.md](../../../docs/sonnen-dial-hardware.md) voor de exacte productchecklist en bring-up volgorde.

## Wat zit erin

- Ronde status-UI voor SOC, PV, verbruik, net en batterijvermogen.
- Encoder-menu: `STATUS`, `AUTO`, `CHARGE`, `DISCH`, `DIM`/`SLEEP`.
- Setpoint-flow met bewuste bevestiging: draai naar `CHARGE` of `DISCH`, druk, draai wattage, druk nogmaals om te verzenden.
- Lange druk dimt of schakelt uit; in setpoint-modus annuleert lange druk eerst.
- Auto-dim en optionele auto-poweroff voor batterijgebruik.
- Wi-Fi gaat standaard na elke Sonnen-request uit voor lager energieverbruik.
- Adaptieve status-refresh: sneller bij laden/ontladen, rustiger bij weinig batterijvermogen, en automatische retry na statusfouten.
- Alle Sonnen-paden, HTTP-methodes, limieten, Wi-Fi en token zitten in `sonnen_config.h`.
- Schrijfacties staan standaard uit met `SONNEN_ALLOW_WRITES 0`; status uitlezen kan dus veilig eerst getest worden.
- `SONNEN_DEMO_MODE 1` test de UI zonder Wi-Fi of batterij.
- SOC gebruikt bij voorkeur `USOC`, omdat dat overeenkomt met de gebruikers/app-weergave. `RSOC` blijft fallback.
- `BAT` toont positief bij laden en negatief bij ontladen. De Sonnen API levert `Pac_total_W` andersom, dus de UI draait dit teken bewust om.
- Geen aparte JSON-library nodig; de firmware leest alleen de bekende top-level Sonnen-statusvelden.

## Configureren

Maak bij voorkeur `sonnen_config.h` met de probe-tool, zodat C++ strings en defaults goed staan:

```sh
scripts/sonnen-probe make-config --wifi-ssid YOUR_WIFI --wifi-password YOUR_PASSWORD --host 192.168.1.50 --token YOUR_TOKEN
```

De generator laat `SONNEN_ALLOW_WRITES` standaard op `0`. Zet writes pas aan wanneer `STATUS` betrouwbaar werkt en je de write-endpoints hebt gecontroleerd.

Voor maximale batterijduur blijft `SONNEN_WIFI_OFF_AFTER_REQUEST` standaard `1`. Na een API-call of mislukte Wi-Fi-poging gaat de radio uit. Zet dit alleen op `0` als je liever sneller achter elkaar status/action calls doet dan energie bespaart.

De status-refresh is adaptief: `SONNEN_ACTIVE_REFRESH_MS` geldt wanneer de batterij actief laadt of ontlaadt boven `SONNEN_ACTIVE_POWER_THRESHOLD_W`; `SONNEN_IDLE_REFRESH_MS` geldt bij weinig batterijvermogen. Als een statuscall faalt, probeert de firmware automatisch opnieuw na `SONNEN_ERROR_REFRESH_MS`, ook zonder aan de draaiknop te zitten.

Voor de eerste hardwaretest mag `SONNEN_DEMO_MODE` tijdelijk op `1`. Dan kun je scherm, encoder, knop en dimmen testen zonder Wi-Fi of Sonnenbatterie. Zet deze voor echte statusmetingen terug op `0`.

`SONNEN_ENABLE_POWER_OFF` staat standaard op `0`. Dan dimt de `SLEEP`/`DIM` actie alleen het scherm en schakelt een lange druk niet echt uit. Zet dit pas op `1` nadat wake uit power-off betrouwbaar is getest op jouw M5 Dial.

Controleer de status-API eerst vanaf de laptop:

```sh
scripts/sonnen-probe status --host 192.168.1.50 --token YOUR_TOKEN
```

Wil je de M5 Dial Wi-Fi/HTTP-flow testen zonder echte Sonnenbatterie, start dan op je laptop:

```sh
scripts/sonnen-mock --host 0.0.0.0 --port 8766
```

Genereer daarna een config met je laptop-IP en poort `8766`.

`sonnen_config.h` staat in `.gitignore`, zodat lokale secrets niet worden meegenomen.

Let op: in deze workspace wordt `arduino/` lokaal genegeerd via `.git/info/exclude`. Gebruik `git add -f arduino/sketchbook/SonnenDialRemote` als deze firmware later bewust mee moet in een commit.

## Build

Vanaf de repo-root:

```sh
scripts/sonnen-dial check
scripts/sonnen-dial libs
scripts/sonnen-dial compile
```

Upload, met je eigen poort:

```sh
scripts/sonnen-dial ports
scripts/sonnen-dial upload /dev/cu.usbmodemXXXX
```

## Bedienconcept

- Draaien bladert door acties.
- Korte druk op `STATUS`: ververs status.
- Korte druk op `AUTO`: zet terug naar self-consumption via de geconfigureerde configuratiecall, alleen als `SONNEN_ALLOW_WRITES` aan staat.
- Korte druk op `CHARGE` of `DISCH`: open wattagekeuze.
- In wattagekeuze: draaien past vermogen aan, korte druk bevestigt. Bij `SONNEN_ALLOW_WRITES 0` toont de firmware `Writes locked` en verstuurt niets.
- Lange druk: annuleren of dimmen. Alleen bij `SONNEN_ENABLE_POWER_OFF 1` schakelt hij echt uit.

In demo-modus toont `STATUS` gesimuleerde waarden en worden alle schrijfacties geblokkeerd met `Demo only`.
