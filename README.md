# Messer VIP Bot - PM2 Installation

Discord Bot für automatisches VIP-Verlängern bei Nahkampfkills auf HLL CRCON Servern.

## Voraussetzungen auf Linux Server

```bash
# Python 3 installieren (falls nicht vorhanden)
sudo apt update
sudo apt install python3 python3-pip python3-venv

# PM2 installieren (falls nicht vorhanden)
sudo npm install -g pm2
```

## Installation

1. Dateien auf Server hochladen:
```bash
# Mit scp oder FileZilla alle Dateien in ein Verzeichnis kopieren, z.B.:
# /home/username/messer-vip-bot/
```

2. Ins Verzeichnis wechseln:
```bash
cd /home/username/messer-vip-bot/
```

3. Python Abhängigkeiten installieren:
```bash
pip3 install -r requirements.txt
```

4. Umgebungsvariablen konfigurieren:
```bash
cp .env.example .env
nano .env
# Fülle die Werte ein und speichere mit CTRL+X, dann Y, dann Enter
```

## Bot mit PM2 starten

```bash
# Bot starten
pm2 start ecosystem.config.js

# Status prüfen
pm2 status

# Logs anschauen
pm2 logs messer-vip-bot

# Bot stoppen
pm2 stop messer-vip-bot

# Bot neustarten
pm2 restart messer-vip-bot

# Bot aus PM2 entfernen
pm2 delete messer-vip-bot
```

## PM2 beim Systemstart automatisch starten

```bash
# Aktuellen PM2-Status speichern
pm2 save

# PM2 beim Boot starten
pm2 startup
# Führe den angezeigten Befehl aus (meist mit sudo)
```

## Logs

Die Logs werden automatisch in `./logs/` gespeichert:
- `err.log` - Fehler
- `out.log` - Normale Ausgabe
- `combined.log` - Beides kombiniert

## Nützliche PM2 Befehle

```bash
pm2 list              # Alle laufenden Prozesse
pm2 monit             # Live-Monitoring
pm2 logs --lines 100  # Letzte 100 Log-Zeilen
pm2 flush             # Log-Dateien leeren
pm2 reload all        # Alle Apps neu laden
```

## Troubleshooting

### Bot startet nicht
```bash
# Manuell testen
python3 main.py

# Python-Pfad prüfen
which python3

# Falls anderer Python-Pfad nötig, in ecosystem.config.js anpassen
```

### Abhängigkeiten fehlen
```bash
# Neu installieren
pip3 install -r requirements.txt --user
```

### .env wird nicht geladen
```bash
# Prüfen ob .env Datei existiert und lesbar ist
ls -la .env
cat .env
```
