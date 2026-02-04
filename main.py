import os
import re
import time
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv
import urllib3

load_dotenv()

API_TOKEN = os.getenv("CRCON_API_TOKEN")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

if not API_TOKEN:
    print("FEHLER: CRCON_API_TOKEN nicht gesetzt!")
    exit()

servers = [
    {"name": "Server 1", "base_url": os.getenv("SERVER1_URL")},
    {"name": "Server 2", "base_url": os.getenv("SERVER2_URL")},
    {"name": "Server 3", "base_url": os.getenv("SERVER3_URL")},
]

for i, server in enumerate(servers, 1):
    if not server["base_url"]:
        print(f"FEHLER: SERVER{i}_URL nicht gesetzt!")
        exit()

# Nahkampfwaffen
NAHKAMPF_WAFFEN = {
    "m3 knife",
    "feldspaten",
    "fairbairn-sykes",
    "fairbairn–sykes",
    "mpl-50 spade",
    "mpl-50 spaten"
}

# Blacklist: Diese IDs bekommen PM aber kein VIP
VIP_BLACKLIST = {
    "76561198859268589"  # Lexman
}

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

for server in servers:
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"})
    session.verify = False
    server["session"] = session

    response = session.get(f"{server['base_url']}/api/get_status")
    if response.status_code != 200:
        print(f"Auth fehlgeschlagen für {server['base_url']}")
        exit()
    data = response.json()
    server["name"] = data.get("server_name") or data.get("name") or server["name"]
    print(f"Verbunden mit: {server['name']}")

server_states = {
    server["base_url"]: {"last_max_id": 0, "seen_log_ids": set()}
    for server in servers
}


def get_historical_logs(server):
    payload = {"limit": 500}
    response = server["session"].post(f"{server['base_url']}/api/get_historical_logs", json=payload)
    if response.status_code == 200:
        return response.json().get("result", [])
    return []


def get_vip_expiration(server, steam_id):
    response = server["session"].get(f"{server['base_url']}/api/get_vip_ids")
    if response.status_code == 200:
        vips = response.json().get("result", [])
        for vip in vips:
            if vip.get("player_id") == steam_id:
                return vip.get("vip_expiration")
    return None


def extend_24h_vip_on_server(server, steam_id):
    current_exp = get_vip_expiration(server, steam_id)
    print(f"DEBUG: Current VIP expiration for {steam_id} on {server['name']}: {current_exp or 'None'}")

    if current_exp and current_exp.startswith("3000-"):
        print(f"DEBUG: Lifetime VIP detected – skipping extension.")
        return False, current_exp

    # Remove existing VIP if any (harmless if none)
    remove_payload = {"player_id": steam_id}
    remove_response = server["session"].post(f"{server['base_url']}/api/remove_vip", json=remove_payload)
    print(f"DEBUG: Remove VIP response: {remove_response.status_code} - {remove_response.text[:100]}")

    # Parse current_exp if exists (robust for formats with/without 'T' or 'Z')
    if current_exp:
        current_exp = current_exp.removesuffix("Z").removesuffix("+00:00")  # Clean up timezone if present
        try:
            # Try ISO with 'T' (and optional milliseconds)
            base_time = datetime.fromisoformat(current_exp)
        except ValueError:
            try:
                # Try without 'T' (e.g., "2026-01-17 00:00:00"), with optional milliseconds
                if '.' in current_exp:
                    current_exp = current_exp.split('.')[0]  # Remove milliseconds if present
                base_time = datetime.strptime(current_exp, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                print(f"DEBUG: Parse failed for {current_exp} – fallback to now.")
                base_time = datetime.now(timezone.utc)
        base_time = base_time.replace(tzinfo=timezone.utc)
    else:
        base_time = datetime.now(timezone.utc)

    new_base = base_time + timedelta(days=1)
    new_exp = new_base.isoformat().replace("+00:00", "Z")  # Format: YYYY-MM-DDTHH:MM:SS.mmmmmmZ (wie im Testcode)
    print(f"DEBUG: Calculated new expiration: {new_exp}")

    payload = {
        "player_id": steam_id,
        "expiration": new_exp,
        "description": "+24h für Nahkampfkill"
    }
    response = server["session"].post(f"{server['base_url']}/api/add_vip", json=payload)
    print(f"DEBUG: Add VIP response: {response.status_code} - {response.text[:100]}")

    return response.status_code == 200, new_exp


def send_private_message(server, player_id, player_name, message):
    payload = {"player_id": player_id, "message": message}
    response = server["session"].post(f"{server['base_url']}/api/message_player", json=payload)
    if response.status_code == 200:
        print(f"PM gesendet an {player_name} ({player_id}) auf {server['name']}")
    else:
        print(f"PM-Fehler auf {server['name']}: {response.status_code} - {response.text}")


def send_discord_log(msg):
    if DISCORD_WEBHOOK_URL:
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
        except:
            pass


print("\n=== NAHKAMPFKILL-BOT LÄUFT – +24 STUNDEN VIP PRO SERVER ===\n")
print("Fix: Expiration-Format angepasst an Testcode (YYYY-MM-DDTHH:MM:SS.mmmmmmZ, mit Millisekunden, Z statt +00:00)\n")
print("Neu: Teamkills werden ignoriert – kein VIP/PM dafür\n")
print("PM wird immer gesendet bei Nahkampfkill (außer bei Teamkills)\n")

while True:
    for server in servers:
        state = server_states[server["base_url"]]

        logs = get_historical_logs(server)
        if not logs:
            continue

        new_logs = [log for log in logs if log.get("id", 0) > state["last_max_id"]]

        if new_logs:
            state["last_max_id"] = max(log.get("id", 0) for log in logs)

        for log in reversed(new_logs):
            log_id = log.get("id")
            if log_id in state["seen_log_ids"]:
                continue
            state["seen_log_ids"].add(log_id)

            log_type = log.get("type", "").upper()
            if "KILL" not in log_type or "TEAM KILL" in log_type:
                continue  # Ignoriere alles ohne "KILL" oder mit "TEAM KILL"

            killer_name = log.get("player1_name") or "Unbekannt"
            killer_id = log.get("player1_id")
            if not killer_id:
                continue
            victim_name = log.get("player2_name") or "Unbekannt"
            content = str(log.get("content", "")).lower()

            weapon = "unbekannt"
            if "with" in content:
                parts = content.split("with")
                if len(parts) > 1:
                    weapon = parts[-1].strip().strip("'\"")

            if weapon in NAHKAMPF_WAFFEN:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_msg = f"[{ts}] Nahkampfkill auf {server['name']}: {killer_name} ({killer_id}) hat {victim_name} mit {weapon.upper()} gekillt"

                # Prüfen ob Spieler auf Blacklist steht
                if killer_id in VIP_BLACKLIST:
                    pm_text = f"Super Nahkampfkill gegen {victim_name} mit {weapon.upper()}! +24 Stunden VIP auf diesem Server!"
                    log_msg += " → Blacklist: Kein VIP vergeben + PM gesendet"
                    send_private_message(server, killer_id, killer_name, pm_text)
                else:
                    extended, _ = extend_24h_vip_on_server(server, killer_id)

                    # Immer PM senden (außer bei Teamkills, was hier schon gefiltert ist)
                    pm_text = f"Super Nahkampfkill gegen {victim_name} mit {weapon.upper()}!"
                    if extended:
                        pm_text += " +24 Stunden VIP auf diesem Server!"
                        log_msg += " → +24h VIP verlängert/gegeben + PM gesendet"
                    else:
                        pm_text += " Weiter so!"  # Lifetime VIP
                        log_msg += " → Lifetime VIP – keine Verlängerung + PM gesendet"

                    send_private_message(server, killer_id, killer_name, pm_text)

                print(log_msg)
                send_discord_log(log_msg)

        if len(state["seen_log_ids"]) > 2000:
            state["seen_log_ids"] = set(list(state["seen_log_ids"])[-1000:])

    time.sleep(5)