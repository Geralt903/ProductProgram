import sys
import time
import threading
from collections import deque
from datetime import datetime
import paho.mqtt.client as mqtt

BROKER_ADDRESS = "20.205.107.61"  # 还是那个服务器
TOPIC = "test/stm32"
SEND_INTERVAL_SEC = 5
WINDOW_SEC = 30 * 60
LOG_PATH = "keyboard_to_mqtt.log"
PER_ITEM_DELAY_SEC = 0.1


def input_loop(buffer, lock, stop_event):
    while not stop_event.is_set():
        data = sys.stdin.buffer.readline()
        if not data:
            stop_event.set()
            break
        ts = time.time()
        with lock:
            buffer.append((ts, data))
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} {data.hex()}\n")


def main():
    client = mqtt.Client()
    client.connect(BROKER_ADDRESS, 1883, 60)
    client.loop_start()

    buffer = deque()
    lock = threading.Lock()
    stop_event = threading.Event()

    t = threading.Thread(target=input_loop, args=(buffer, lock, stop_event), daemon=True)
    t.start()

    print("Keyboard -> MQTT publisher (raw bytes, batch every 5s, last 30 minutes)")
    print("Type a line and press Enter to send. Ctrl+C to quit.")

    try:
        while not stop_event.is_set():
            cycle_start = time.time()
            cutoff = cycle_start - WINDOW_SEC
            with lock:
                while buffer and buffer[0][0] < cutoff:
                    buffer.popleft()
                if not buffer:
                    time.sleep(SEND_INTERVAL_SEC)
                    continue
                snapshot = [data for _, data in buffer]

            required = len(snapshot) * PER_ITEM_DELAY_SEC
            if required > SEND_INTERVAL_SEC:
                print("ERROR: 时间不足，数据过多")
            else:
                for data in snapshot:
                    client.publish(TOPIC, data)
                    time.sleep(PER_ITEM_DELAY_SEC)

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