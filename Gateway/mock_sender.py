import time
import json
import argparse
from datetime import datetime
import paho.mqtt.client as mqtt

# Configuration
BROKER_ADDRESS = "20.205.107.61"
TOPIC = "test/stm32"
BAUD_RATE = 9600
SEND_INTERVAL_SEC = 5

# Mock data - all fields set to 0
MOCK_PACKET = {
    "id": 0,
    "device_id": 0,
    "digits": "00000000000000000000000000000000000",  # 35 zeros
    "receive_at": 0,  # Will be set to current time
    "temperature_raw": 0,
    "temperature_celsius": 0.0,
    "humidity_raw": 0,
    "humidity_percent": 0.0,
    "distance_mm": 0.0,
    "mq4_concentration": 0,
    "mq136_concentration": 0
}


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


def main(broker_address=None, topic=None, interval=None):
    if broker_address is None:
        broker_address = BROKER_ADDRESS
    if topic is None:
        topic = TOPIC
    if interval is None:
        interval = SEND_INTERVAL_SEC

    # Initialize MQTT client
    try:
        print(f"[INFO] Connecting to MQTT broker: {broker_address}:1883")
        
        userdata = {'connected': False}
        
        if hasattr(mqtt, "CallbackAPIVersion"):
            client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata=userdata)
        else:
            client = mqtt.Client(userdata=userdata)
        
        # Set callbacks
        client.on_connect = on_mqtt_connect
        client.on_disconnect = on_mqtt_disconnect
        
        # Try connection with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"[INFO] MQTT connection attempt {attempt + 1}/{max_retries}...")
                client.connect(broker_address, 1883, keepalive=60)
                client.loop_start()
                
                # Wait for connection callback
                time.sleep(2)
                
                if userdata['connected']:
                    print("[OK] MQTT connection successful!")
                    break
                elif attempt < max_retries - 1:
                    print(f"[WARNING] MQTT connection not confirmed, retrying...")
                    time.sleep(2)
                else:
                    print("[ERROR] MQTT connection failed after retries")
                    return
                    
            except Exception as e:
                print(f"[WARNING] Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"[ERROR] Failed to connect to MQTT broker after {max_retries} attempts: {e}")
                    return
                    
    except Exception as e:
        print(f"[ERROR] MQTT initialization failed: {e}")
        return

    # Main sending loop
    try:
        print(f"[INFO] Starting mock data sender (interval: {interval}s)...")
        sequence = 0
        
        while True:
            if not userdata['connected']:
                print("[WARNING] MQTT not connected, waiting...")
                time.sleep(interval)
                continue
            
            # Prepare mock packet with current timestamp
            packet = MOCK_PACKET.copy()
            packet['receive_at'] = datetime.now().isoformat()
            
            # Optional: increment device_id for each send to distinguish messages
            packet['device_id'] = sequence
            
            # Convert to JSON
            payload = json.dumps(packet)
            
            try:
                client.publish(topic, payload)
                print(f"[SEND #{sequence}] Published: device_id={packet['device_id']}, "
                      f"temperature_celsius={packet['temperature_celsius']:.1f}°C, "
                      f"receive_at={packet['receive_at']}")
                sequence += 1
            except Exception as e:
                print(f"[ERROR] Failed to publish: {e}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
    finally:
        print("[INFO] Cleaning up...")
        client.loop_stop()
        client.disconnect()
        print("[INFO] Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock MQTT sender with zero-filled data")
    parser.add_argument("--broker", default=BROKER_ADDRESS,
                        help=f"MQTT broker address (default: {BROKER_ADDRESS})")
    parser.add_argument("--topic", default=TOPIC,
                        help=f"MQTT topic (default: {TOPIC})")
    parser.add_argument("--interval", type=int, default=SEND_INTERVAL_SEC,
                        help=f"Send interval in seconds (default: {SEND_INTERVAL_SEC})")
    
    args = parser.parse_args()
    
    print(f"[CONFIG] Broker: {args.broker}, Topic: {args.topic}, Interval: {args.interval}s")
    main(broker_address=args.broker, topic=args.topic, interval=args.interval)
