import json
import re
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import serial

BROKER_ADDRESS = "20.205.107.61"
TOPIC = "test/stm32"
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600
SEND_INTERVAL_SEC = 5

# Packet format from STM32:
# "%010lu%05u%05u%05u%05u%05u"
DEVICE_ID_LEN = 10
FIELD_LEN = 5
PACKET_LEN = DEVICE_ID_LEN + FIELD_LEN * 5  # 35
PACKET_RE = re.compile(rf"^\\d{{{PACKET_LEN}}}$")

TEMP_SCALE = 100.0
HUM_SCALE = 100.0
DIST_SCALE = 10.0


def iso_utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def decode_ascii_packet_text(text: str) -> dict:
    if not PACKET_RE.fullmatch(text):
        raise ValueError("packet format invalid")

    idx = 0
    device_id_s = text[idx:idx + DEVICE_ID_LEN]
    idx += DEVICE_ID_LEN

    temperature_s = text[idx:idx + FIELD_LEN]
    idx += FIELD_LEN
    humidity_s = text[idx:idx + FIELD_LEN]
    idx += FIELD_LEN
    distance_s = text[idx:idx + FIELD_LEN]
    idx += FIELD_LEN
    mq4_s = text[idx:idx + FIELD_LEN]
    idx += FIELD_LEN
    mq136_s = text[idx:idx + FIELD_LEN]

    temperature_i = int(temperature_s)
    humidity_i = int(humidity_s)
    distance_i = int(distance_s)
    mq4_i = int(mq4_s)
    mq136_i = int(mq136_s)

    return {
        "device_id": int(device_id_s),
        "device_id_text": device_id_s,
        "temperature_c": temperature_i / TEMP_SCALE,
        "humidity_percent": humidity_i / HUM_SCALE,
        "distance_cm": distance_i / DIST_SCALE,
        "mq4_ppm": float(mq4_i),
        "mq136_ppm": float(mq136_i),
        "temperature_raw": temperature_i,
        "humidity_raw": humidity_i,
        "distance_raw": distance_i,
        "mq4_raw": mq4_i,
        "mq136_raw": mq136_i,
        "packet_text": text,
    }


def serial_loop(ser, shared_state, lock, stop_event):
    while not stop_event.is_set():
        raw = ser.readline()
        if not raw:
            time.sleep(0.01)
            continue

        text = raw.decode("ascii", errors="ignore").strip()
        if not text:
            continue

        try:
            decoded = decode_ascii_packet_text(text)
        except Exception:
            continue

        payload_obj = {
            "ts": iso_utc_now(),
            **decoded,
        }
        payload_text = json.dumps(payload_obj, ensure_ascii=False, separators=(",", ":"))

        with lock:
            shared_state["latest_payload"] = payload_text
            shared_state["latest_ts"] = payload_obj["ts"]


def main():
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

    client = mqtt.Client()
    client.connect(BROKER_ADDRESS, 1883, 60)
    client.loop_start()

    shared_state = {"latest_payload": None, "latest_ts": None}
    lock = threading.Lock()
    stop_event = threading.Event()

    t = threading.Thread(target=serial_loop, args=(ser, shared_state, lock, stop_event), daemon=True)
    t.start()

    print(f"Listening {SERIAL_PORT}, publish latest packet every {SEND_INTERVAL_SEC}s -> {TOPIC}")
    try:
        while True:
            time.sleep(SEND_INTERVAL_SEC)
            with lock:
                payload_text = shared_state["latest_payload"]
                latest_ts = shared_state["latest_ts"]
            if payload_text is None:
                continue

            client.publish(TOPIC, payload_text.encode("utf-8"))
            print(f"published latest ts={latest_ts}")
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        client.loop_stop()
        client.disconnect()
        ser.close()


if __name__ == "__main__":
    main()
