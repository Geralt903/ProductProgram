import json
import os
import sys
import time
import threading
from collections import deque
from datetime import datetime, timezone
import sqlite3
import paho.mqtt.client as mqtt

BROKER_ADDRESS = "20.205.107.61"  # MQTT 服务器地址
TOPIC = "test/stm32"
SEND_INTERVAL_SEC = 5
CLEAR_INTERVAL_SEC = 30 * 60
PER_ITEM_DELAY_SEC = 0.1

LOG_DIR = os.path.join(os.path.dirname(__file__), "log")
DB_PATH = os.path.join(LOG_DIR, "keyboard_to_mqtt.db")


def init_db():
    os.makedirs(LOG_DIR, exist_ok=True)
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
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM logs")
        conn.commit()
    finally:
        conn.close()


def iso_utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def write_log(payload: bytes,
              topic: str | None = None,
              ts: str | None = None,
              payload_text: str | None = None):
    ts_value = ts or iso_utc_now()
    payload_hex = payload.hex()
    if payload_text is None:
        try:
            payload_text = payload.decode("utf-8")
        except Exception:
            payload_text = None

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO logs (ts, source, topic, payload_hex, payload_text) VALUES (?, ?, ?, ?, ?)",
            (ts_value, "keyboard_to_mqtt", topic, payload_hex, payload_text),
        )
        conn.commit()
    finally:
        conn.close()


def input_loop(buffer, lock, stop_event):
    while not stop_event.is_set():
        data = sys.stdin.buffer.readline()
        if not data:
            stop_event.set()
            break
        ts_iso = iso_utc_now()
        try:
            text = data.decode("utf-8")
        except Exception:
            text = data.decode("utf-8", errors="replace")
        text = text.rstrip("\r\n")
        with lock:
            buffer.append((ts_iso, text))
        write_log(data, TOPIC, ts=ts_iso, payload_text=text)


def main():
    init_db()

    client = mqtt.Client()
    client.connect(BROKER_ADDRESS, 1883, 60)
    client.loop_start()

    buffer = deque()
    lock = threading.Lock()
    stop_event = threading.Event()

    t = threading.Thread(target=input_loop, args=(buffer, lock, stop_event), daemon=True)
    t.start()

    print("Keyboard -> MQTT publisher (json, poll every 5s)")
    print("Type a line and press Enter to send. Ctrl+C to quit.")

    last_cleanup = time.time()
    try:
        while not stop_event.is_set():
            cycle_start = time.time()
            with lock:
                if buffer:
                    snapshot = list(buffer)
                    buffer.clear()
                else:
                    snapshot = []

            for ts_iso, text in snapshot:
                payload = json.dumps(
                    {"ts": ts_iso, "data": text},
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                client.publish(TOPIC, payload.encode("utf-8"))
                time.sleep(PER_ITEM_DELAY_SEC)

            now = time.time()
            if now - last_cleanup >= CLEAR_INTERVAL_SEC:
                cleanup_all()
                last_cleanup = now

            elapsed = time.time() - cycle_start
            if elapsed < SEND_INTERVAL_SEC:
                time.sleep(SEND_INTERVAL_SEC - elapsed)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
