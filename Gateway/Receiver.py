import time
import serial
import json
import os
import paho.mqtt.client as mqtt

PACKET_DIGITS = 35
TEMP_SCALE = 100.0
HUM_SCALE = 100.0
DIST_SCALE = 100.0

SERIAL_PORT = "/dev/ttyUSB0"
SERIAL_BAUD = 9600
READ_CHUNK = 128

LOG_PATH = "data_log.csv"
INITIAL_SAMPLES = 3
INITIAL_INTERVAL_S = 5
PERIODIC_INTERVAL_S = 3600

MQTT_HOST = "20.205.107.61"
MQTT_PORT = 1883
MQTT_TOPIC = "stm/test"


def parse_digit_packet(digits: str) -> dict:
    if len(digits) != PACKET_DIGITS or not digits.isdigit():
        raise ValueError(f"unexpected packet digits: {digits!r}")
    temperature_raw = int(digits[10:15])
    humidity_raw = int(digits[15:20])
    distance_raw = int(digits[20:25])
    mq4_raw = int(digits[25:30])
    mq136_raw = int(digits[30:35])
    return {
        "device_id": int(digits[0:10]),
        "temperature_raw": temperature_raw,
        "humidity_raw": humidity_raw,
        "distance_raw": distance_raw,
        "mq4": mq4_raw,
        "mq136": mq136_raw,
        "temperature": temperature_raw / TEMP_SCALE,
        "humidity": humidity_raw / HUM_SCALE,
        "distance": distance_raw / DIST_SCALE,
    }


def ensure_log_header(path: str) -> None:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("ts,digits,device_id,temp,hum,dist,mq4,mq136\n")


def append_record(path: str, ts: str, digits: str, parsed: dict) -> None:
    line = (
        f"{ts},{digits},{parsed['device_id']:010d},"
        f"{parsed['temperature']:.2f},{parsed['humidity']:.2f},"
        f"{parsed['distance']:.2f},{parsed['mq4']},{parsed['mq136']}\n"
    )
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(line)


def create_mqtt_client() -> mqtt.Client:
    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    return client


def publish_mqtt(client: mqtt.Client, ts: str, digits: str, parsed: dict) -> None:
    payload = json.dumps(
        {
            "ts": ts,
            "digits": digits,
            "device_id": parsed["device_id"],
            "temperature": parsed["temperature"],
            "humidity": parsed["humidity"],
            "distance": parsed["distance"],
            "mq4": parsed["mq4"],
            "mq136": parsed["mq136"],
        }
    )
    client.publish(MQTT_TOPIC, payload)


def receiver_loop(ser: serial.Serial, mqtt_client: mqtt.Client | None) -> None:
    print("=== Receiver started (waiting data) ===")
    digit_buffer = []
    initial_remaining = INITIAL_SAMPLES
    next_store_time = time.time()

    while True:
        try:
            chunk = ser.read(READ_CHUNK)
            if not chunk:
                continue
            for byte in chunk:
                if 48 <= byte <= 57:
                    digit_buffer.append(chr(byte))
                else:
                    if digit_buffer:
                        digit_buffer.clear()

            while len(digit_buffer) >= PACKET_DIGITS:
                digits = "".join(digit_buffer[:PACKET_DIGITS])
                del digit_buffer[:PACKET_DIGITS]

                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                parsed = parse_digit_packet(digits)
                print(f"[{ts}] RX(digits): {digits}")
                print(
                    f"[{ts}] id={parsed['device_id']:010d} "
                    f"temp={parsed['temperature']:.2f} "
                    f"hum={parsed['humidity']:.2f} "
                    f"dist={parsed['distance']:.2f} "
                    f"mq4={parsed['mq4']} "
                    f"mq136={parsed['mq136']}"
                )

                now = time.time()
                if now >= next_store_time:
                    ensure_log_header(LOG_PATH)
                    append_record(LOG_PATH, ts, digits, parsed)
                    if mqtt_client is not None:
                        publish_mqtt(mqtt_client, ts, digits, parsed)
                    if initial_remaining > 0:
                        initial_remaining -= 1
                        if initial_remaining > 0:
                            next_store_time = now + INITIAL_INTERVAL_S
                        else:
                            next_store_time = now + PERIODIC_INTERVAL_S
                    else:
                        next_store_time = now + PERIODIC_INTERVAL_S

        except Exception as e:
            print("Receiver error:", e)
            time.sleep(0.1)


def main() -> None:
    ser = None
    mqtt_client = None
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        print("Serial opened:", ser.isOpen())
        mqtt_client = create_mqtt_client()
        receiver_loop(ser, mqtt_client)
    except KeyboardInterrupt:
        pass
    finally:
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        if ser and ser.isOpen():
            ser.close()
        print("Program Exited")


if __name__ == "__main__":
    main()
