# Avalon Mini3 für Home Assistant

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch**

Lokale Integration für den Bitcoin-Miner bzw. Heizlüfter **Canaan Avalon Mini3**. Sie spricht die
CGMiner-API des Miners auf TCP-Port 4028 an – ohne Cloud und ohne Konto.

## Funktionen

- Auswahl **Betriebsmodus**: Standby, Heizung Eco, Heizung Super, Mining, Nacht. Aus dem Standby
  wird der Miner automatisch aufgeweckt.
- Schalter **Display** und Taste **Neustart**
- Sensoren für Leistung, Hashrate, Temperaturen (Eingang, Ausgang, Hashboard, Chips),
  Lüfterdrehzahl und -leistung, Pool, akzeptierte/abgelehnte Shares, besten Share, gefundene
  Blöcke und Netzwerk-Schwierigkeit
- Diagnose-Sensoren für Laufzeit, Systemstatus, Hardwarefehler, Pool-Ping und Chipfrequenz
- Binärsensor für die Pool-Verbindung
- Der Miner wird über seine MAC-Adresse erkannt. Ändert sich die IP-Adresse, ihn einfach erneut
  hinzufügen oder *Neu konfigurieren* wählen – Entitäten und Verlauf bleiben erhalten.

Getestet mit Firmware `25022401_cb28ba7`.

## Installation

### HACS

1. HACS → ⋮ → *Benutzerdefinierte Repositories* → `https://github.com/damian-himmel/ha-avalon-mini3`
   mit Kategorie *Integration* hinzufügen.
2. **Avalon Mini3** installieren und Home Assistant neu starten.

### Manuell

`custom_components/avalon_mini3` in den Ordner `custom_components` der Home-Assistant-Konfiguration
kopieren und neu starten.

## Einrichtung

*Einstellungen → Geräte & Dienste → Integration hinzufügen → Avalon Mini3*, dann die IP-Adresse des
Miners eingeben. Im Router eine feste Adresse für ihn reservieren.

## Hinweise

- Nach einem Befehl dauert es etwa zwei Sekunden, bis der Miner den neuen Zustand meldet.
- Abfrageintervall: 15 Sekunden.

## Danksagung

Der Aufbau ist angelehnt an [avalon_nano3s](https://github.com/jinx-22/avalon_nano3s) von
@jinx-22.

## Marken

Avalon und das Avalon-Logo sind Marken von Canaan Inc. Dieses Projekt steht in keiner Verbindung zu
Canaan und wird nicht von Canaan unterstützt.

## Lizenz

[MIT](LICENSE)
