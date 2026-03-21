"""
树莓派 LoRa 网关 - Raspberry Pi LoRa Gateway
===========================================

功能：
1. 接收来自串口的加密 LoRa 数据包（12 字节）
2. 验证 MIC 和解密数据
3. 解析应用层数据后通过 MQTT 发送到云服务器
4. 同时可模拟生成 LoRa 数据包用于测试

用法：
  # 模式 1: 只接收串口数据
  python lora_gateway.py --port /dev/ttyUSB0 --mode receiver
  
  # 模式 2: 只生成测试数据
  python lora_gateway.py --mode simulator
  
  # 模式 3: 接收 + 模拟（同时运行）
  python lora_gateway.py --port /dev/ttyUSB0 --mode both
  
  # 模式 4: Windows 测试
  python lora_gateway.py --port COM3 --broker 127.0.0.1
"""

import time
import threading
from collections import deque
from datetime import datetime
import json
import platform
import sys
import argparse
import struct
import hmac
import hashlib

# 串口和MQTT库
import serial
import paho.mqtt.client as mqtt

# LoRa协议库（动态导入处理）
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
MQTT_TOPIC_RECEIVER = "lora/gateway/receiver"  # 接收到的传感器数据
MQTT_TOPIC_SIMULATOR = "lora/gateway/simulator"  # 模拟生成的测试数据
MQTT_PORT = 1883
MQTT_TIMEOUT_SEC = 5
MQTT_KEEPALIVE = 60

# 串口配置
if platform.system() == "Windows":
    DEFAULT_SERIAL_PORT = "COM3"
else:
    DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"  # 树莓派默认
DEFAULT_BAUD_RATE = 9600

# LoRa 协议配置
LORA_PACKET_SIZE = 12
PROTOCOL_HEADER = 0x11
SHARED_KEY = b'ThisIsA128BitKey'  # 16 字节 AES-128 密钥

# 应用配置
SEND_INTERVAL_SEC = 5
WINDOW_SEC = 30 * 60  # 30 分钟窗口
LOG_PATH = "lora_gateway.log"
PER_ITEM_DELAY_SEC = 0.1


# ============================================================================
# LoRa 数据包解析
# ============================================================================

class LoRaPacketParser:
    """LoRa 数据包解析器"""
    
    def __init__(self, shared_key: bytes = SHARED_KEY):
        """初始化解析器"""
        if len(shared_key) != 16:
            raise ValueError("Key must be 16 bytes for AES-128")
        self.shared_key = shared_key
    
    def parse_packet(self, raw_data: bytes) -> dict:
        """
        解析 LoRa 数据包
        
        Args:
            raw_data: 12 字节的原始数据包
            
        Returns:
            解析后的 JSON 对象，或 None（如果解析失败）
            
        Raises:
            ValueError: 包长度不正确或 MIC 校验失败
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Crypto library not available")
        
        # ===== 步骤 1: 包长检查 =====
        if len(raw_data) != LORA_PACKET_SIZE:
            raise ValueError(f"Invalid packet length: {len(raw_data)}, expected {LORA_PACKET_SIZE}")
        
        # ===== 步骤 2: 字节分割 =====
        header = raw_data[0]
        seq_bytes = raw_data[1:3]
        encrypted_payload = raw_data[3:8]
        mic_received = raw_data[8:12]
        
        # ===== 步骤 3: MIC 验证 =====
        data_to_verify = bytes([header]) + seq_bytes + encrypted_payload
        computed_mic = hmac.new(
            self.shared_key,
            data_to_verify,
            hashlib.sha256
        ).digest()[:4]
        
        if computed_mic != mic_received:
            raise ValueError("MIC verification failed - packet may be corrupted")
        
        # ===== 步骤 4: 解密 =====
        padding_len = 16 - (len(encrypted_payload) % 16)
        padded = encrypted_payload + bytes([padding_len] * padding_len)
        
        cipher = AES.new(self.shared_key, AES.MODE_ECB)
        plaintext_padded = cipher.decrypt(padded)
        plaintext_payload = plaintext_padded[:5]
        
        # ===== 步骤 5: 应用层解析 =====
        seq_id = struct.unpack('>H', seq_bytes)[0]
        
        temp_raw = struct.unpack('>h', plaintext_payload[0:2])[0]
        temperature = round(temp_raw / 100.0, 2)
        
        humidity = plaintext_payload[2]
        battery = plaintext_payload[3]
        status_code = plaintext_payload[4]
        
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # ===== 步骤 6: 返回结构化数据 =====
        return {
            "meta": {
                "protocol_version": f"0x{header:02X}",
                "sequence_id": seq_id,
                "packet_size": LORA_PACKET_SIZE
            },
            "data": {
                "temperature": temperature,
                "humidity": humidity,
                "battery_level": battery,
                "status": {
                    "code": status_code,
                    "description": self._get_status_description(status_code)
                }
            },
            "timestamp": timestamp,
            "raw_hex": self._packet_to_hex_string(raw_data)
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
    
    @staticmethod
    def _packet_to_hex_string(packet: bytes) -> str:
        """将数据包转换为十六进制字符串"""
        return ' '.join(f'{b:02X}' for b in packet)


# ============================================================================
# LoRa 数据包生成器（用于测试）
# ============================================================================

class LoRaPacketSimulator:
    """LoRa 数据包模拟生成器"""
    
    def __init__(self, shared_key: bytes = SHARED_KEY, sequence_offset: int = 0):
        """初始化模拟器"""
        if len(shared_key) != 16:
            raise ValueError("AES-128 key must be 16 bytes")
        self.shared_key = shared_key
        self.sequence = sequence_offset
    
    def generate_packet(self, 
                       temperature: float,
                       humidity: int,
                       battery_level: int,
                       status_code: int = 0) -> bytes:
        """生成完整的 12 字节数据包"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Crypto library not available")
        
        # 构建明文 payload (5 bytes)
        plaintext_payload = struct.pack('>h B B B',
                                       int(temperature * 100),
                                       humidity,
                                       battery_level,
                                       status_code)
        
        # 加密 payload
        padding_len = 16 - (len(plaintext_payload) % 16)
        padded = plaintext_payload + bytes([padding_len] * padding_len)
        
        cipher = AES.new(self.shared_key, AES.MODE_ECB)
        encrypted_full = cipher.encrypt(padded)
        encrypted_payload = encrypted_full[:5]
        
        # 构建包头和序号
        header = struct.pack('B', PROTOCOL_HEADER)
        seq_bytes = struct.pack('>H', self.sequence)
        
        # 计算 MIC
        data_to_mac = header + seq_bytes + encrypted_payload
        hmac_obj = hmac.new(self.shared_key, data_to_mac, hashlib.sha256)
        mic = hmac_obj.digest()[:4]
        
        # 拼接完整数据包
        packet = header + seq_bytes + encrypted_payload + mic
        
        self.sequence += 1
        
        return packet
    
    @staticmethod
    def packet_to_hex_string(packet: bytes) -> str:
        """将数据包转换为十六进制字符串"""
        return ' '.join(f'{b:02X}' for b in packet)


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
# 接收线程
# ============================================================================

def serial_receiver_loop(ser, buffer, lock, stop_event, parser=None):
    """
    串口接收线程 - 读取 12 字节的 LoRa 数据包
    """
    packet_buffer = bytearray()
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
            packet_buffer.extend(data)
            
            # 检查是否有完整的 12 字节包
            while len(packet_buffer) >= LORA_PACKET_SIZE:
                # 查找协议头 0x11
                if packet_buffer[0] != PROTOCOL_HEADER:
                    packet_buffer.pop(0)
                    continue
                
                # 提取 12 字节包
                packet_data = bytes(packet_buffer[:LORA_PACKET_SIZE])
                del packet_buffer[:LORA_PACKET_SIZE]
                
                # 尝试解析
                try:
                    if parser:
                        parsed = parser.parse_packet(packet_data)
                        ts = time.time()
                        with lock:
                            buffer.append((ts, json.dumps(parsed)))
                        
                        with open(LOG_PATH, "a", encoding="utf-8") as f:
                            f.write(f"{datetime.now().isoformat()} [RX] {parsed['raw_hex']} -> OK\n")
                        
                        print(f"[RX] Seq={parsed['meta']['sequence_id']:04d} "
                              f"Temp={parsed['data']['temperature']:.2f}°C "
                              f"Humidity={parsed['data']['humidity']}% "
                              f"Battery={parsed['data']['battery_level']}% "
                              f"Status={parsed['data']['status']['description']}")
                    else:
                        # 如果没有解析器，直接添加原始数据
                        ts = time.time()
                        with lock:
                            buffer.append((ts, packet_data.hex()))
                        print(f"[RX] Raw packet: {packet_data.hex()}")
                    
                except Exception as e:
                    with open(LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now().isoformat()} [RX_ERROR] {packet_data.hex()} -> {str(e)}\n")
                    print(f"[ERROR] Parse error: {e}")
        
        except Exception as e:
            print(f"[ERROR] Error in serial receiver thread: {e}")
            time.sleep(1)


# ============================================================================
# 模拟线程
# ============================================================================

def simulator_loop(buffer, lock, stop_event, simulator=None):
    """
    模拟线程 - 定期生成虚拟 LoRa 数据包
    """
    if not simulator:
        return
    
    temperature = 20.0
    humidity = 50
    battery = 90
    
    while not stop_event.is_set():
        try:
            # 生成变化的数据
            temperature += 0.1
            humidity = 50 + (int(time.time()) % 20) - 10
            battery = 90 - (int(time.time()) % 30000) // 1000
            
            if battery < 10:
                battery = 90
            
            # 生成数据包
            packet = simulator.generate_packet(
                temperature=min(temperature, 40.0),  # 限制温度范围
                humidity=max(0, min(humidity, 100)),
                battery_level=max(0, min(battery, 100)),
                status_code=0
            )
            
            # 解析生成的包（用于日志）
            try:
                parser = LoRaPacketParser()
                parsed = parser.parse_packet(packet)
                ts = time.time()
                with lock:
                    buffer.append((ts, json.dumps(parsed)))
                
                with open(LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat()} [SIM] {parsed['raw_hex']} -> OK\n")
                
                print(f"[SIM] Seq={parsed['meta']['sequence_id']:04d} "
                      f"Temp={parsed['data']['temperature']:.2f}°C "
                      f"Humidity={parsed['data']['humidity']}% "
                      f"Battery={parsed['data']['battery_level']}% "
                      f"Status={parsed['data']['status']['description']}")
            except Exception as e:
                print(f"[ERROR] Simulator parse error: {e}")
            
            # 模拟发送间隔
            time.sleep(SEND_INTERVAL_SEC)
        
        except Exception as e:
            print(f"[ERROR] Error in simulator thread: {e}")
            time.sleep(1)


# ============================================================================
# MQTT 发送线程
# ============================================================================

def mqtt_sender_loop(client, userdata, buffer, lock, stop_event, topic):
    """
    MQTT 发送线程 - 定期发送缓冲区中的数据
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
            
            # 发送数据
            if new_data:
                for data in new_data:
                    try:
                        client.publish(topic, data, qos=1)
                        last_publish_count += 1
                        time.sleep(PER_ITEM_DELAY_SEC)
                    except Exception as e:
                        print(f"[ERROR] Failed to publish: {e}")
                
                print(f"[MQTT] Published {len(new_data)} messages to '{topic}' "
                      f"(total published: {last_publish_count})")
            
            time.sleep(SEND_INTERVAL_SEC)
        
        except Exception as e:
            print(f"[ERROR] Error in MQTT sender thread: {e}")
            time.sleep(SEND_INTERVAL_SEC)


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='树莓派 LoRa 网关 - Raspberry Pi LoRa Gateway'
    )
    parser.add_argument('--port', default=DEFAULT_SERIAL_PORT,
                       help=f'Serial port (default: {DEFAULT_SERIAL_PORT})')
    parser.add_argument('--baud', type=int, default=DEFAULT_BAUD_RATE,
                       help=f'Baud rate (default: {DEFAULT_BAUD_RATE})')
    parser.add_argument('--broker', default=BROKER_ADDRESS,
                       help=f'MQTT broker address (default: {BROKER_ADDRESS})')
    parser.add_argument('--mode', default='receiver',
                       choices=['receiver', 'simulator', 'both'],
                       help='Operating mode: receiver (serial), simulator (generate), or both')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("树莓派 LoRa 网关 - Raspberry Pi LoRa Gateway")
    print("=" * 70)
    print(f"[CONFIG] Mode: {args.mode}")
    print(f"[CONFIG] MQTT Broker: {args.broker}:{MQTT_PORT}")
    print(f"[CONFIG] Log file: {LOG_PATH}")
    
    # 检查加密库
    if not CRYPTO_AVAILABLE:
        print("[ERROR] pycryptodome not installed!")
        print("[INFO] Install with: pip install pycryptodome")
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
                return
        
        except Exception as e:
            print(f"[WARNING] Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print(f"[ERROR] Failed to connect to MQTT: {e}")
                return
    
    # 初始化缓冲区和同步机制
    buffer = deque()
    lock = threading.Lock()
    stop_event = threading.Event()
    
    threads = []
    
    # 接收线程
    if args.mode in ['receiver', 'both']:
        try:
            print(f"[INFO] Opening serial port: {args.port} @ {args.baud} baud")
            ser = serial.Serial(args.port, args.baud, timeout=1)
            print("[OK] Serial port connected")
            
            lora_parser = LoRaPacketParser()
            
            t = threading.Thread(
                target=serial_receiver_loop,
                args=(ser, buffer, lock, stop_event, lora_parser),
                daemon=True
            )
            threads.append((t, "Receiver"))
            t.start()
        
        except serial.SerialException as e:
            print(f"[ERROR] Failed to open serial port {args.port}: {e}")
            print("[INFO] Available ports: /dev/ttyUSB0, /dev/ttyACM0 (Raspberry Pi)")
            print("[INFO]                  COM3, COM4, COM5 (Windows)")
            return
    
    # 模拟线程
    if args.mode in ['simulator', 'both']:
        simulator = LoRaPacketSimulator(sequence_offset=1)
        t = threading.Thread(
            target=simulator_loop,
            args=(buffer, lock, stop_event, simulator),
            daemon=True
        )
        threads.append((t, "Simulator"))
        t.start()
    
    # MQTT 发送线程
    for mode_name, topic in [('receiver', MQTT_TOPIC_RECEIVER), ('simulator', MQTT_TOPIC_SIMULATOR)]:
        if args.mode in [mode_name, 'both']:
            t = threading.Thread(
                target=mqtt_sender_loop,
                args=(mqtt_client, userdata, buffer, lock, stop_event, topic),
                daemon=True
            )
            threads.append((t, f"MQTT-{mode_name}"))
            t.start()
    
    print("[INFO] All threads started, press Ctrl+C to stop")
    print()
    
    try:
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        stop_event.set()
        
        # 等待所有线程结束
        for t, name in threads:
            print(f"[INFO] Waiting for {name} thread...")
            t.join(timeout=5)
        
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        
        print("[OK] Shutdown complete")


if __name__ == '__main__':
    main()
