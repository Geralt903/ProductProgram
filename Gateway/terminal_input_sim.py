import os
import sys
import time
from datetime import datetime, timezone
import sqlite3
import serial

SERIAL_PORT = "/dev/ttyS0"
BAUD_RATE = 9600
CLEAR_INTERVAL_SEC = 30 * 60

LOG_DIR = os.path.join(os.path.dirname(__file__), "log")
DB_PATH = os.path.join(LOG_DIR, "terminal_input_sim.db")


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


def write_log(payload: bytes):
    ts = iso_utc_now()
    payload_hex = payload.hex()
    try:
        payload_text = payload.decode("utf-8")
    except Exception:
        payload_text = None

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO logs (ts, source, topic, payload_hex, payload_text) VALUES (?, ?, ?, ?, ?)",
            (ts, "terminal_input_sim", None, payload_hex, payload_text),
        )
        conn.commit()
    finally:
        conn.close()


def main():
    init_db()

    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    last_cleanup = time.time()
    try:
        print("Keyboard -> Serial input simulator")
        print("Type a line and press Enter to send. Ctrl+C to quit.")
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            if line.endswith("\n"):
                data = line
            else:
                data = line + "\n"
            raw = data.encode("utf-8")
            ser.write(raw)
            ser.flush()
            write_log(raw)
            now = time.time()
            if now - last_cleanup >= CLEAR_INTERVAL_SEC:
                cleanup_all()
                last_cleanup = now
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()


if __name__ == "__main__":
    main()
