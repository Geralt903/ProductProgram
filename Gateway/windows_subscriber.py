import os
import time
import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

try:
    import sqlite3
except Exception:
    sqlite3 = None

BROKER_ADDRESS = "20.205.107.61"
TOPIC = "test/stm32"
CLEAR_INTERVAL_SEC = 30 * 60

LOG_DIR = os.path.join(os.path.dirname(__file__), "log")
DB_PATH = os.path.join(LOG_DIR, "windows_subscriber.db")
LOG_PATH = os.path.join(LOG_DIR, "windows_subscriber.log")

LAST_CLEANUP = 0.0


def init_db():
    os.makedirs(LOG_DIR, exist_ok=True)
    if sqlite3 is None:
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS logs ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "ts TEXT NOT NULL, "
            "source TEXT, "
            "topic TEXT, "
            "payload_hex TEXT, "
            "payload_text TEXT)"
        )
        conn.commit()
    finally:
        conn.close()


def cleanup_all():
    if sqlite3 is None:
        try:
            with open(LOG_PATH, "w", encoding="utf-8"):
                pass
        except Exception:
            pass
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM logs")
        conn.commit()
    finally:
        conn.close()


def iso_utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def write_log(topic: str, payload: bytes):
    ts = iso_utc_now()
    payload_hex = payload.hex()
    try:
        payload_text = payload.decode("utf-8")
    except Exception:
        payload_text = None

    if sqlite3 is None:
        record = {
            "ts": ts,
            "source": "windows_subscriber",
            "topic": topic,
            "payload_hex": payload_hex,
            "payload_text": payload_text,
        }
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO logs (ts, source, topic, payload_hex, payload_text) VALUES (?, ?, ?, ?, ?)",
            (ts, "windows_subscriber", topic, payload_hex, payload_text),
        )
        conn.commit()
    finally:
        conn.close()


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected")
        client.subscribe(TOPIC)
    else:
        print(f"Connect failed: {rc}")


def on_message(client, userdata, msg):
    global LAST_CLEANUP
    print(f"[{msg.topic}] {msg.payload}")
    write_log(msg.topic, msg.payload)

    now = time.time()
    if now - LAST_CLEANUP >= CLEAR_INTERVAL_SEC:
        cleanup_all()
        LAST_CLEANUP = now


def main():
    global LAST_CLEANUP
    init_db()
    LAST_CLEANUP = time.time()
    if sqlite3 is None:
        print(f"sqlite3 not available, using file log: {LOG_PATH}")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_ADDRESS, 1883, 60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
