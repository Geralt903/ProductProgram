import time
import threading
from collections import deque
from datetime import datetime
import serial
import paho.mqtt.client as mqtt
import json
import platform
import sys
import argparse

# Default configuration
BROKER_ADDRESS = "20.205.107.61"
TOPIC = "test/stm32"
# Auto-detect serial port based on OS
if platform.system() == "Windows":
    DEFAULT_SERIAL_PORT = "COM3"  # Change to COM3, COM4, etc. as needed for Windows
else:
    DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"  # Raspberry Pi default (same as serial_listener_simple.py)
DEFAULT_BAUD_RATE = 9600
SEND_INTERVAL_SEC = 5
WINDOW_SEC = 30 * 60
LOG_PATH = "terminal_serial.log"
PER_ITEM_DELAY_SEC = 0.1
MQTT_TIMEOUT_SEC = 5  # MQTT connection timeout

PACKET_DIGITS = 35
TEMP_SCALE = 100.0
HUM_SCALE = 100.0
DIST_SCALE = 100.0


def parse_digit_packet(digits: str) -> dict:
    """Parse 35-digit packet into JSON format matching Java entity"""
    if len(digits) != PACKET_DIGITS or not digits.isdigit():
        return None
    
    try:
        device_id = int(digits[0:10])
        temperature_raw = int(digits[10:15])
        humidity_raw = int(digits[15:20])
        distance_raw = int(digits[20:25])
        mq4_raw = int(digits[25:30])
        mq136_raw = int(digits[30:35])
        
        return {
            "id": None,  # 由数据库自动生成
            "device_id": device_id,
            "digits": digits,
            "receive_at": datetime.now().isoformat(),
            "temperature_raw": temperature_raw,
            "temperature_celsius": round(temperature_raw / TEMP_SCALE, 2),
            "humidity_raw": humidity_raw,
            "humidity_percent": round(humidity_raw / HUM_SCALE, 2),
            "distance_mm": round(distance_raw / DIST_SCALE, 2),
            "mq4_concentration": mq4_raw,
            "mq136_concentration": mq136_raw
        }
    except Exception as e:
        print(f"Parse error: {e}")
        return None


def on_mqtt_connect(client, userdata, connect_flags, reason_code, properties=None):
    """MQTT connection callback"""
    if reason_code == 0 or reason_code.is_success():
        print("[OK] MQTT connected successfully!")
        userdata['connected'] = True
    else:
        print(f"[ERROR] MQTT connection failed with code: {reason_code}")
        userdata['connected'] = False


def on_mqtt_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
    """MQTT disconnection callback"""
    print(f"[WARNING] MQTT disconnected with code: {reason_code}")
    userdata['connected'] = False


def on_mqtt_connect_fail(client, userdata, flags=None):
    """MQTT connection failure callback (legacy)"""
    print("[ERROR] MQTT connection failed (legacy callback)")
    userdata['connected'] = False


def serial_loop(ser, buffer, lock, stop_event):
    """Serial reading thread - removes spaces and collects complete 35-digit packets"""
    digit_buffer = []
    last_success = time.time()
    
    while not stop_event.is_set():
        try:
            data = ser.read(128)
            if not data:
                time.sleep(0.01)
                # Check if no data for too long
                if time.time() - last_success > 30:
                    print("[WARNING] No serial data received for 30 seconds")
                    last_success = time.time()
                continue
            
            last_success = time.time()

            # Process each byte: extract digits, skip spaces/newlines
            for byte in data:
                if 48 <= byte <= 57:  # ASCII '0'-'9'
                    digit_buffer.append(chr(byte))
                elif byte in (10, 13, 32):  # '\n', '\r', ' ' - skip these
                    pass
                else:
                    # Non-digit, non-space character: clear buffer
                    if digit_buffer:
                        digit_buffer.clear()
            
            # Check if we have a complete packet
            while len(digit_buffer) >= PACKET_DIGITS:
                digits = "".join(digit_buffer[:PACKET_DIGITS])
                del digit_buffer[:PACKET_DIGITS]
                
                # Parse and add to buffer
                parsed = parse_digit_packet(digits)
                if parsed:
                    ts = time.time()
                    with lock:
                        buffer.append((ts, json.dumps(parsed)))
                    with open(LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now().isoformat()} {digits} -> {parsed}\n")
                    print(f"[RX] device_id={parsed['device_id']:010d} "
                          f"temperature_celsius={parsed['temperature_celsius']:.2f}°C "
                          f"humidity_percent={parsed['humidity_percent']:.2f}% "
                          f"distance_mm={parsed['distance_mm']:.2f} "
                          f"mq4_concentration={parsed['mq4_concentration']} "
                          f"mq136_concentration={parsed['mq136_concentration']}")
        except Exception as e:
            print(f"[ERROR] Error in serial thread: {e}")
            time.sleep(1)


def main(serial_port=None, baud_rate=None, broker_address=None, topic=None):
    # Support command-line arguments for Raspberry Pi
    if serial_port is None:
        serial_port = DEFAULT_SERIAL_PORT
    if baud_rate is None:
        baud_rate = DEFAULT_BAUD_RATE
    if broker_address is None:
        broker_address = BROKER_ADDRESS
    if topic is None:
        topic = TOPIC
    
    # Initialize serial connection with error handling
    ser = None
    try:
        print(f"[INFO] Connecting to serial port: {serial_port} @ {baud_rate} baud")
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print("[OK] Serial port connected")
    except serial.SerialException as e:
        print(f"[ERROR] Failed to open serial port {serial_port}: {e}")
        print("[INFO] For Raspberry Pi, try: /dev/ttyUSB0, /dev/ttyACM0")
        print("[INFO] For Windows, try: COM3, COM4, COM5, etc.")
        return
    
    # Initialize MQTT client with timeout and callbacks
    try:
        print(f"[INFO] Connecting to MQTT broker: {BROKER_ADDRESS}:1883")
        
        # Create client with userdata for storing connection state
        userdata = {'connected': False}
        
        if hasattr(mqtt, "CallbackAPIVersion"):
            client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata=userdata)
        else:
            client = mqtt.Client(userdata=userdata)
        
        # Set callbacks
        client.on_connect = on_mqtt_connect
        client.on_disconnect = on_mqtt_disconnect
        
        # Try connection with longer timeout and retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"[INFO] MQTT connection attempt {attempt + 1}/{max_retries}...")
                client.connect(BROKER_ADDRESS, 1883, keepalive=60)
                client.loop_start()
                
                # Wait a bit for connection callback
                time.sleep(2)
                
                if userdata['connected']:
                    print("[OK] MQTT connection successful!")
                    break
                elif attempt < max_retries - 1:
                    print(f"[WARNING] MQTT connection not confirmed, retrying...")
                    time.sleep(2)
                else:
                    print("[ERROR] MQTT connection failed after retries")
                    ser.close()
                    return
                    
            except Exception as e:
                print(f"[WARNING] Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"[ERROR] Failed to connect to MQTT broker after {max_retries} attempts: {e}")
                    print(f"[INFO] Check: broker address ('{BROKER_ADDRESS}'), network connectivity, firewall")
                    ser.close()
                    return
                    
    except Exception as e:
        print(f"[ERROR] MQTT initialization failed: {e}")
        ser.close()
        return

    buffer = deque()
    lock = threading.Lock()
    stop_event = threading.Event()
    last_sent_time = 0  # Track last sent timestamp for incremental sending

    t = threading.Thread(target=serial_loop, args=(ser, buffer, lock, stop_event), daemon=True)
    t.start()

    try:
        print("[INFO] Starting main loop (incremental send mode)...")
        while not stop_event.is_set():
            cycle_start = time.time()
            cutoff = cycle_start - WINDOW_SEC
            new_data = []
            
            with lock:
                # Remove expired data
                while buffer and buffer[0][0] < cutoff:
                    buffer.popleft()
                
                if not buffer:
                    time.sleep(SEND_INTERVAL_SEC)
                    continue
                
                # Only get NEW data (incremental)
                new_data = [data for ts, data in buffer if ts > last_sent_time]
                
                # Update last_sent_time to the latest timestamp
                if buffer:
                    last_sent_time = max(ts for ts, _ in buffer)

            # Check MQTT connection before publishing
            if not userdata['connected']:
                print("[WARNING] MQTT not connected, skipping publish")
                time.sleep(SEND_INTERVAL_SEC)
                continue

            # Send only new data (incremental)
            if new_data:
                print(f"[SEND] Publishing {len(new_data)} new messages")
                for data in new_data:
                    try:
                        client.publish(TOPIC, data)
                    except Exception as e:
                        print(f"[ERROR] Failed to publish: {e}")
                    time.sleep(PER_ITEM_DELAY_SEC)
            else:
                print("[INFO] No new data to send")

            elapsed = time.time() - cycle_start
            if elapsed < SEND_INTERVAL_SEC:
                time.sleep(SEND_INTERVAL_SEC - elapsed)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
    finally:
        print("[INFO] Cleaning up...")
        stop_event.set()
        client.loop_stop()
        client.disconnect()
        ser.close()
        print("[INFO] Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serial MQTT Gateway with 35-digit packet parsing")
    parser.add_argument("--port", default=DEFAULT_SERIAL_PORT, 
                        help=f"Serial port path (default: {DEFAULT_SERIAL_PORT})")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD_RATE, 
                        help=f"Baud rate (default: {DEFAULT_BAUD_RATE})")
    parser.add_argument("--broker", default=BROKER_ADDRESS,
                        help=f"MQTT broker address (default: {BROKER_ADDRESS})")
    parser.add_argument("--topic", default=TOPIC,
                        help=f"MQTT topic (default: {TOPIC})")
    
    args = parser.parse_args()
    
    # Update global settings from command line
    BROKER_ADDRESS = args.broker
    TOPIC = args.topic
    
    print(f"[CONFIG] Port: {args.port}, Baud: {args.baud}, Broker: {args.broker}, Topic: {args.topic}")
    main(serial_port=args.port, baud_rate=args.baud)