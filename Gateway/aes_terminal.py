"""
AES Terminal - 35位数字 -> LoRa加密包 -> MQTT
================================================

功能：
1. 从串口接收 35 位数字（可能带空格）
2. 解析为应用层数据（温度、湿度、电量、状态）
3. 转换为 12 字节加密的 LoRa 包
4. 同时发送两个 MQTT 消息：
   - 物理层：12 字节二进制包（Hex 格式）
   - 应用层：JSON 格式（解析后的数据）

用法：
  python aes_terminal.py --port /dev/ttyUSB0 --broker 20.205.107.61
  python aes_terminal.py --port COM3 --broker 127.0.0.1
"""

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
import struct
import hmac
import hashlib

try:
    from Crypto.Cipher import AES
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("[WARNING] pycryptodome not found. Install with: pip install pycryptodome")


# ============================================================================
# 配置常量
# ============================================================================

# MQTT 配置
BROKER_ADDRESS = "20.205.107.61"
MQTT_TOPIC = "test/stm32"  # 统一使用test/stm32话题
MQTT_PORT = 1883
MQTT_TIMEOUT_SEC = 5
MQTT_KEEPALIVE = 60

# 串口配置
if platform.system() == "Windows":
    DEFAULT_SERIAL_PORT = "COM3"
else:
    DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD_RATE = 9600

# LoRa 协议配置
SHARED_KEY = b'ThisIsA128BitKey'  # 16 字节 AES-128 密钥
PROTOCOL_HEADER = 0x11
LORA_PACKET_SIZE = 12

# 35位数字格式配置
PACKET_DIGITS = 35
TEMP_SCALE = 100.0
HUM_SCALE = 100.0
DIST_SCALE = 100.0

# 应用配置
SEND_INTERVAL_SEC = 5
WINDOW_SEC = 30 * 60  # 30 分钟窗口
LOG_PATH = "aes_terminal.log"
PER_ITEM_DELAY_SEC = 0.1


# ============================================================================
# 35位数字解析函数
# ============================================================================

def parse_digit_packet(digits: str) -> dict:
    """解析 35 位数字包为应用层数据"""
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


# ============================================================================
# LoRa 数据包生成器
# ============================================================================

class LoRaPacketGenerator:
    """将应用层数据转换为 LoRa 加密包"""
    
    def __init__(self, shared_key: bytes = SHARED_KEY, sequence_offset: int = 0):
        """初始化生成器"""
        if len(shared_key) != 16:
            raise ValueError("AES-128 key must be 16 bytes")
        self.shared_key = shared_key
        self.sequence = sequence_offset
    
    def generate_from_35digit(self, parsed_35digit: dict) -> dict:
        """
        从 35 位数字的解析结果生成 LoRa 包
        
        Args:
            parsed_35digit: 由 parse_digit_packet 返回的字典
            
        Returns:
            {
                'packet_hex': '11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4',
                'packet_bytes': b'...',
                'json': {...}
            }
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Crypto library not available")
        
        if not parsed_35digit:
            return None
        
        # ===== 步骤 1: 构建明文 payload (5 bytes) =====
        # 这里我们使用 35位中的核心数据：温度、湿度、电量、状态
        # 状态码从 device_id 或固定为 0
        
        temp_celsius = parsed_35digit['temperature_celsius']
        humidity = int(parsed_35digit['humidity_percent'])
        battery = 95  # 默认电量 95% (示例)，可根据实际情况调整
        status_code = 0  # 默认正常
        
        # 温度 int16_t，乘以 100
        temp_raw = int(temp_celsius * 100)
        plaintext_payload = struct.pack('>h B B B',
                                       temp_raw,
                                       humidity,
                                       battery,
                                       status_code)
        
        # ===== 步骤 2: 加密 payload =====
        padding_len = 16 - (len(plaintext_payload) % 16)
        padded = plaintext_payload + bytes([padding_len] * padding_len)
        
        cipher = AES.new(self.shared_key, AES.MODE_ECB)
        encrypted_full = cipher.encrypt(padded)
        encrypted_payload = encrypted_full[:5]
        
        # ===== 步骤 3: 构建包头和序号 =====
        header = struct.pack('B', PROTOCOL_HEADER)
        seq_bytes = struct.pack('>H', self.sequence)
        
        # ===== 步骤 4: 计算 MIC =====
        data_to_mac = header + seq_bytes + encrypted_payload
        hmac_obj = hmac.new(self.shared_key, data_to_mac, hashlib.sha256)
        mic = hmac_obj.digest()[:4]
        
        # ===== 步骤 5: 拼接完整数据包 =====
        packet = header + seq_bytes + encrypted_payload + mic
        
        # ===== 步骤 6: 构建返回结果 =====
        seq_id = self.sequence
        self.sequence += 1
        
        # 物理层数据（12字节）
        packet_hex = ' '.join(f'{b:02X}' for b in packet)
        
        # 应用层数据（JSON）
        application_data = {
            "meta": {
                "protocol_version": f"0x{PROTOCOL_HEADER:02X}",
                "sequence_id": seq_id,
                "packet_size": LORA_PACKET_SIZE,
                "source": "35digit_converter"
            },
            "data": {
                "temperature": temp_celsius,
                "humidity": humidity,
                "battery_level": battery,
                "status": {
                    "code": status_code,
                    "description": self._get_status_description(status_code)
                },
                "source_info": {
                    "device_id": parsed_35digit['device_id'],
                    "distance_mm": parsed_35digit['distance_mm'],
                    "mq4": parsed_35digit['mq4_concentration'],
                    "mq136": parsed_35digit['mq136_concentration']
                }
            },
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "raw_hex": packet_hex
        }
        
        return {
            'packet_hex': packet_hex,
            'packet_bytes': packet,
            'json': application_data
        }
    
    @staticmethod
    def _get_status_description(code: int) -> str:
        """根据状态码返回描述"""
        status_map = {
            0: "Normal",
            1: "Fault",
            2: "Low Battery",
            3: "Sensor Error"
        }
        return status_map.get(code, f"Unknown({code})")


# ============================================================================
# MQTT 回调函数
# ============================================================================

def on_mqtt_connect(client, userdata, connect_flags, reason_code, properties=None):
    """MQTT 连接回调"""
    if reason_code == 0 or reason_code.is_success():
        print("[OK] MQTT connected successfully!")
        userdata['connected'] = True
    else:
        print(f"[ERROR] MQTT connection failed with code: {reason_code}")
        userdata['connected'] = False


def on_mqtt_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
    """MQTT 断开回调"""
    print(f"[WARNING] MQTT disconnected with code: {reason_code}")
    userdata['connected'] = False


# ============================================================================
# 串口接收线程
# ============================================================================

def serial_loop(ser, buffer, lock, stop_event):
    """
    串口读取线程 - 接收 35 位数字（去掉空格）
    与 terminal.py 逻辑相同
    """
    digit_buffer = []
    last_success = time.time()
    
    while not stop_event.is_set():
        try:
            data = ser.read(128)
            if not data:
                time.sleep(0.01)
                if time.time() - last_success > 30:
                    print("[WARNING] No serial data received for 30 seconds")
                    last_success = time.time()
                continue
            
            last_success = time.time()

            # 处理每个字节：提取数字，跳过空格/换行
            for byte in data:
                if 48 <= byte <= 57:  # ASCII '0'-'9'
                    digit_buffer.append(chr(byte))
                elif byte in (10, 13, 32):  # '\n', '\r', ' ' - 跳过
                    pass
                else:
                    # 非数字、非空格字符：清除缓冲
                    if digit_buffer:
                        digit_buffer.clear()
            
            # 检查是否有完整的 35 位包
            while len(digit_buffer) >= PACKET_DIGITS:
                digits = "".join(digit_buffer[:PACKET_DIGITS])
                del digit_buffer[:PACKET_DIGITS]
                
                # 解析 35 位数字
                parsed = parse_digit_packet(digits)
                if parsed:
                    ts = time.time()
                    with lock:
                        buffer.append((ts, json.dumps(parsed)))
                    
                    with open(LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now().isoformat()} [RX_35DIGIT] {digits} -> OK\n")
                    
                    print(f"[RX_35D] device_id={parsed['device_id']:010d} "
                          f"temp={parsed['temperature_celsius']:.2f}°C "
                          f"humidity={parsed['humidity_percent']:.2f}% "
                          f"distance={parsed['distance_mm']:.2f}mm")
        
        except Exception as e:
            print(f"[ERROR] Error in serial thread: {e}")
            time.sleep(1)


# ============================================================================
# 数据转换与 MQTT 发送线程
# ============================================================================

def conversion_and_publish_loop(client, userdata, buffer, lock, stop_event, generator):
    """
    数据转换线程：
    1. 接收 35 位数字的解析数据
    2. 转换为 LoRa 加密包
    3. 发送到 MQTT（物理层 + 应用层）
    """
    last_sent_time = 0
    last_publish_count = 0
    
    while not stop_event.is_set():
        try:
            cycle_start = time.time()
            cutoff = cycle_start - WINDOW_SEC
            new_data = []
            
            with lock:
                # 删除过期数据
                while buffer and buffer[0][0] < cutoff:
                    buffer.popleft()
                
                if not buffer:
                    time.sleep(SEND_INTERVAL_SEC)
                    continue
                
                # 只获取新数据
                new_data = [data for ts, data in buffer if ts > last_sent_time]
                
                if buffer:
                    last_sent_time = max(ts for ts, _ in buffer)
            
            # 检查 MQTT 连接
            if not userdata['connected']:
                print("[WARNING] MQTT not connected, skipping publish")
                time.sleep(SEND_INTERVAL_SEC)
                continue
            
            # 转换并发送数据
            if new_data:
                for data_str in new_data:
                    try:
                        parsed_35digit = json.loads(data_str)
                        
                        # 转换为 LoRa 包
                        lora_packet = generator.generate_from_35digit(parsed_35digit)
                        
                        if not lora_packet:
                            continue
                        
                        # 发送加密包数据到MQTT（十六进制字符串格式）
                        mqtt_payload = lora_packet['packet_hex']
                        client.publish(MQTT_TOPIC, mqtt_payload, qos=1)
                        
                        last_publish_count += 1
                        
                        with open(LOG_PATH, "a", encoding="utf-8") as f:
                            f.write(f"{datetime.now().isoformat()} [CONVERT] "
                                   f"35digit -> {lora_packet['packet_hex']}\n")
                        
                        print(f"[CONVERT] device_id={parsed_35digit['device_id']:010d} "
                              f"-> {lora_packet['packet_hex']}")
                        print(f"[MQTT] Published to '{MQTT_TOPIC}'")
                        
                        time.sleep(PER_ITEM_DELAY_SEC)
                    
                    except Exception as e:
                        print(f"[ERROR] Conversion error: {e}")
                        with open(LOG_PATH, "a", encoding="utf-8") as f:
                            f.write(f"{datetime.now().isoformat()} [CONVERT_ERROR] {str(e)}\n")
            
            time.sleep(SEND_INTERVAL_SEC)
        
        except Exception as e:
            print(f"[ERROR] Error in conversion/publish thread: {e}")
            time.sleep(SEND_INTERVAL_SEC)


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='35位数字 -> LoRa加密包 -> MQTT'
    )
    parser.add_argument('--port', default=DEFAULT_SERIAL_PORT,
                       help=f'Serial port (default: {DEFAULT_SERIAL_PORT})')
    parser.add_argument('--baud', type=int, default=DEFAULT_BAUD_RATE,
                       help=f'Baud rate (default: {DEFAULT_BAUD_RATE})')
    parser.add_argument('--broker', default=BROKER_ADDRESS,
                       help=f'MQTT broker address (default: {BROKER_ADDRESS})')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("AES Terminal - 35位数字 -> LoRa加密包 -> MQTT")
    print("=" * 70)
    print(f"[CONFIG] Serial Port: {args.port}:{args.baud}")
    print(f"[CONFIG] MQTT Broker: {args.broker}:{MQTT_PORT}")
    print(f"[CONFIG] MQTT Topic: {MQTT_TOPIC}")
    print(f"[CONFIG] Log file: {LOG_PATH}")
    print()
    
    # 检查加密库
    if not CRYPTO_AVAILABLE:
        print("[ERROR] pycryptodome not installed!")
        print("[INFO] Install with: pip install pycryptodome")
        return
    
    # 初始化串口
    ser = None
    try:
        print(f"[INFO] Opening serial port: {args.port} @ {args.baud} baud")
        ser = serial.Serial(args.port, args.baud, timeout=1)
        print("[OK] Serial port connected")
    except serial.SerialException as e:
        print(f"[ERROR] Failed to open serial port {args.port}: {e}")
        print("[INFO] For Raspberry Pi, try: /dev/ttyUSB0, /dev/ttyACM0")
        print("[INFO] For Windows, try: COM3, COM4, COM5, etc.")
        return
    
    # 初始化 MQTT 客户端
    userdata = {'connected': False}
    if hasattr(mqtt, "CallbackAPIVersion"):
        mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata=userdata)
    else:
        mqtt_client = mqtt.Client(userdata=userdata)
    
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_disconnect = on_mqtt_disconnect
    
    # 连接 MQTT
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"[INFO] MQTT connection attempt {attempt + 1}/{max_retries}...")
            mqtt_client.connect(args.broker, MQTT_PORT, keepalive=MQTT_KEEPALIVE)
            mqtt_client.loop_start()
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
                print(f"[ERROR] Failed to connect to MQTT: {e}")
                ser.close()
                return
    
    # 初始化数据结构
    buffer = deque()
    lock = threading.Lock()
    stop_event = threading.Event()
    generator = LoRaPacketGenerator(SHARED_KEY, sequence_offset=1)
    
    # 启动线程
    t1 = threading.Thread(target=serial_loop, args=(ser, buffer, lock, stop_event), daemon=True)
    t1.start()
    
    t2 = threading.Thread(
        target=conversion_and_publish_loop,
        args=(mqtt_client, userdata, buffer, lock, stop_event, generator),
        daemon=True
    )
    t2.start()
    
    print("[INFO] All threads started, press Ctrl+C to stop")
    print()
    
    try:
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        stop_event.set()
        
        t1.join(timeout=5)
        t2.join(timeout=5)
        
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        ser.close()
        
        print("[OK] Shutdown complete")


if __name__ == '__main__':
    main()
