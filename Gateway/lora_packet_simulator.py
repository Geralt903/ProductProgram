"""
LoRa 传感器数据包模拟器
模拟生成符合协议的 12 字节加密数据包

协议格式 (12 bytes):
  Byte 0: Protocol Header (0x11)
  Byte 1-2: Sequence Number (Big-Endian)
  Byte 3-7: Encrypted Payload (5 bytes)
  Byte 8-11: MIC (Message Integrity Check, 4 bytes)
"""

import struct
import time
from typing import Tuple, List
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256
import binascii


class LoRaPacketSimulator:
    # 协议常量
    PROTOCOL_HEADER = 0x11
    PAYLOAD_SIZE = 5  # 明文 payload 字节数
    MIC_SIZE = 4  # MIC 字节数
    PACKET_SIZE = 12  # 总包大小
    
    def __init__(self, shared_key: bytes, sequence_offset: int = 0):
        """
        初始化模拟器
        
        Args:
            shared_key: 预共享的 AES-128 密钥 (16 bytes)
            sequence_offset: 序号偏移量，用于重放保护测试
        """
        if len(shared_key) != 16:
            raise ValueError("AES-128 key must be 16 bytes")
        
        self.shared_key = shared_key
        self.sequence = sequence_offset
    
    def build_plaintext_payload(self, 
                               temperature: float,
                               humidity: int,
                               battery_level: int,
                               status_code: int = 0) -> bytes:
        """
        构建明文 payload (5 bytes)
        
        Args:
            temperature: 温度 (℃)，会乘以 100 存储为 int16
            humidity: 湿度 (%)
            battery_level: 电量 (%)
            status_code: 设备状态码
            
        Returns:
            5 字节的明文数据
        """
        # Offset 0-1: int16_t 温度 (大端序), Value / 100.0
        temp_raw = int(temperature * 100)
        
        # Offset 2: uint8_t 湿度
        # Offset 3: uint8_t 电量
        # Offset 4: uint8_t 状态码
        
        payload = struct.pack('>h B B B',
                            temp_raw,
                            humidity,
                            battery_level,
                            status_code)
        
        return payload
    
    def encrypt_payload(self, plaintext: bytes) -> Tuple[bytes, bytes]:
        """
        使用 AES-128-ECB 加密 payload
        
        Args:
            plaintext: 明文 payload (5 bytes)
            
        Returns:
            (加密后的数据, 使用的初始化向量或None)
        """
        if len(plaintext) != self.PAYLOAD_SIZE:
            raise ValueError(f"Plaintext must be {self.PAYLOAD_SIZE} bytes")
        
        # 对于 ECB 模式，需要将 5 字节填充到 16 字节（AES 块大小）
        # 使用 PKCS7 填充
        cipher = AES.new(self.shared_key, AES.MODE_ECB)
        
        # 填充到 16 字节
        padding_len = 16 - (len(plaintext) % 16)
        padded = plaintext + bytes([padding_len] * padding_len)
        
        encrypted_full = cipher.encrypt(padded)
        
        # 只返回前 5 字节的密文
        return encrypted_full[:self.PAYLOAD_SIZE]
    
    def calculate_mic(self,
                     header: bytes,
                     seq_bytes: bytes,
                     encrypted_payload: bytes) -> bytes:
        """
        计算 MIC (Message Integrity Check)
        
        使用 HMAC-SHA256，取前 4 字节作为 MIC
        
        Args:
            header: 协议头 (1 byte)
            seq_bytes: 序号 (2 bytes)
            encrypted_payload: 加密后的 payload (5 bytes)
            
        Returns:
            4 字节的 MIC
        """
        # 拼接要计算的数据
        data_to_mac = header + seq_bytes + encrypted_payload
        
        # 使用 HMAC-SHA256
        hmac = HMAC.new(self.shared_key, data_to_mac, SHA256)
        mic_full = hmac.digest()
        
        # 取前 4 字节作为 MIC
        return mic_full[:self.MIC_SIZE]
    
    def generate_packet(self,
                       temperature: float,
                       humidity: int,
                       battery_level: int,
                       status_code: int = 0) -> bytes:
        """
        生成完整的 12 字节数据包
        
        Args:
            temperature: 温度 (℃)
            humidity: 湿度 (%)
            battery_level: 电量 (%)
            status_code: 设备状态码
            
        Returns:
            12 字节的数据包
        """
        # 步骤 1: 构建明文 payload
        plaintext_payload = self.build_plaintext_payload(
            temperature, humidity, battery_level, status_code
        )
        
        # 步骤 2: 加密 payload
        encrypted_payload = self.encrypt_payload(plaintext_payload)
        
        # 步骤 3: 构建包头和序号
        header = struct.pack('B', self.PROTOCOL_HEADER)
        seq_bytes = struct.pack('>H', self.sequence)  # 大端序
        
        # 步骤 4: 计算 MIC
        mic = self.calculate_mic(header, seq_bytes, encrypted_payload)
        
        # 步骤 5: 拼接完整数据包
        packet = header + seq_bytes + encrypted_payload + mic
        
        # 增加序号，为下一个包做准备
        self.sequence += 1
        
        return packet
    
    def packet_to_hex_string(self, packet: bytes) -> str:
        """将数据包转换为十六进制字符串（便于查看）"""
        return ' '.join(f'{b:02X}' for b in packet)
    
    def parse_packet_structure(self, packet: bytes) -> dict:
        """
        解析数据包结构（用于调试）
        
        Args:
            packet: 12 字节的数据包
            
        Returns:
            包结构字典
        """
        if len(packet) != self.PACKET_SIZE:
            raise ValueError(f"Packet must be {self.PACKET_SIZE} bytes")
        
        header = packet[0]
        seq = struct.unpack('>H', packet[1:3])[0]
        encrypted_payload = packet[3:8]
        mic = packet[8:12]
        
        return {
            'header': f'0x{header:02X}',
            'sequence': seq,
            'encrypted_payload': ' '.join(f'{b:02X}' for b in encrypted_payload),
            'mic': ' '.join(f'{b:02X}' for b in mic),
            'hex_string': self.packet_to_hex_string(packet)
        }


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == '__main__':
    # 预共享密钥 (16 bytes) - 后端应该与前端保持一致
    # 这里使用一个示例密钥，实际应使用安全的密钥管理方式
    SHARED_KEY = b'ThisIsA128BitKey'  # 16 个字符 = 16 bytes
    
    # 创建模拟器实例
    simulator = LoRaPacketSimulator(shared_key=SHARED_KEY, sequence_offset=1)
    
    print("=" * 70)
    print("LoRa 传感器数据包模拟器 - 数据发送示例")
    print("=" * 70)
    print()
    
    # 场景 1: 文档中的标准场景
    print("[场景 1] 标准场景 - 温度 25.65℃, 湿度 60%, 电量 95%, 正常状态")
    print("-" * 70)
    
    packet1 = simulator.generate_packet(
        temperature=25.65,
        humidity=60,
        battery_level=95,
        status_code=0
    )
    
    structure1 = simulator.parse_packet_structure(packet1)
    print(f"序号: {structure1['sequence']}")
    print(f"协议头: {structure1['header']}")
    print(f"加密后 Payload: {structure1['encrypted_payload']}")
    print(f"MIC 校验码: {structure1['mic']}")
    print(f"十六进制字符串: {structure1['hex_string']}")
    print()
    
    # 场景 2: 低温场景
    print("[场景 2] 低温场景 - 温度 -2.00℃, 湿度 45%, 电量 30%, 正常状态")
    print("-" * 70)
    
    packet2 = simulator.generate_packet(
        temperature=-2.00,
        humidity=45,
        battery_level=30,
        status_code=0
    )
    
    structure2 = simulator.parse_packet_structure(packet2)
    print(f"序号: {structure2['sequence']}")
    print(f"协议头: {structure2['header']}")
    print(f"加密后 Payload: {structure2['encrypted_payload']}")
    print(f"MIC 校验码: {structure2['mic']}")
    print(f"十六进制字符串: {structure2['hex_string']}")
    print()
    
    # 场景 3: 异常状态
    print("[场景 3] 异常状态 - 温度 30.80℃, 湿度 70%, 电量 10%, 故障状态(code=1)")
    print("-" * 70)
    
    packet3 = simulator.generate_packet(
        temperature=30.80,
        humidity=70,
        battery_level=10,
        status_code=1
    )
    
    structure3 = simulator.parse_packet_structure(packet3)
    print(f"序号: {structure3['sequence']}")
    print(f"协议头: {structure3['header']}")
    print(f"加密后 Payload: {structure3['encrypted_payload']}")
    print(f"MIC 校验码: {structure3['mic']}")
    print(f"十六进制字符串: {structure3['hex_string']}")
    print()
    
    # 场景 4: 连续生成多个数据包（模拟重放保护）
    print("[场景 4] 连续生成 5 个数据包（显示序号递增）")
    print("-" * 70)
    
    for i in range(5):
        packet = simulator.generate_packet(
            temperature=22.50 + i * 0.5,
            humidity=50 + i * 2,
            battery_level=90 - i * 5,
            status_code=0
        )
        structure = simulator.parse_packet_structure(packet)
        print(f"包 {i+4}: Seq={structure['sequence']}, "
              f"Hex={structure['hex_string']}")
    
    print()
    print("=" * 70)
    print("模拟发送完成")
    print("=" * 70)
