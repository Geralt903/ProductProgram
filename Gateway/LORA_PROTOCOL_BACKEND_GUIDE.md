# LoRa 传感器节点 -> 服务端 通信协议文档

## 概述

本文档定义了 LoRa 传感器节点与后端服务器之间的通信协议，包括物理层数据格式、加密方案和应用层数据结构。

---

## 1. 物理层数据格式 (Physical Layer)

### 包结构

每个数据包严格定长 **12 字节**，结构如下：

| 字节范围 | 字节数 | 字段名称 | 含义 |
|---------|--------|---------|------|
| Byte 0 | 1 | Protocol Header | 协议头，固定值 `0x11` |
| Byte 1-2 | 2 | Sequence Number | 包序号（大端序，用于防重放） |
| Byte 3-7 | 5 | Encrypted Payload | AES-128 加密后的传感器数据 |
| Byte 8-11 | 4 | MIC | 消息完整性校验码（HMAC-SHA256 前 4 字节） |

### 具体示例

**Scenario：温度 25.65℃、湿度 60%、电量 95%、设备正常**

```
原始十六进制数据（12 字节）：
11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4

字节拆解：
┌─────────┬──────────────┬─────────────────────────────────────┬──────────────────────┐
│ Header  │  Sequence    │    Encrypted Payload                │       MIC            │
│  0x11   │  0x00 0x01   │  0xA5 0xB9 0x2D 0x4F 0x88           │ 0xF1 0xE2 0xD3 0xC4  │
│ (1B)    │   (2B)       │        (5B)                         │       (4B)           │
└─────────┴──────────────┴─────────────────────────────────────┴──────────────────────┘
```

---

## 2. 应用层数据定义 (Plaintext Payload)

### 明文 Payload 结构 (5 字节)

加密后的 5 字节数据解密后，包含以下内容（大端序）：

| 偏移 | 数据类型 | 字节数 | 原始示例 | 十进制 | 计算公式 | 物理含义 |
|------|---------|--------|---------|--------|-------------|---------|
| +0 | `int16_t` | 2 | `0x0A05` | 2565 | Value ÷ 100 | 温度 (℃) |
| +2 | `uint8_t` | 1 | `0x3C` | 60 | Value | 湿度 (%) |
| +3 | `uint8_t` | 1 | `0x5F` | 95 | Value | 电量 (%) |
| +4 | `uint8_t` | 1 | `0x00` | 0 | Value | 设备状态码 |

### 解密后示例

```
明文 Payload（5 字节）：
0A 05 3C 5F 00

字段解析：
  Temp High Byte:   0x0A
  Temp Low Byte:    0x05  ──> 组合为 0x0A05 = 2565 ──> 25.65℃
  Humidity:         0x3C  ──> 60%
  Battery:          0x5F  ──> 95%
  Status:           0x00  ──> 0 (正常)
```

---

## 3. 后端接收与处理逻辑 (Backend Processing)

### 3.1 接收流程

```
步骤 1: 读取原始数据
  从串口/网络接收 12 字节数据
  如果包长 < 12，丢弃等待下一包

步骤 2: 字节分割
  header = data[0]              // Byte 0
  seq_high = data[1]             // Byte 1
  seq_low = data[2]              // Byte 2
  encrypted = data[3:8]          // Bytes 3-7 (5 bytes)
  mic_received = data[8:12]      // Bytes 8-11 (4 bytes)

步骤 3: MIC 验证
  header_byte = pack(header)
  seq_bytes = pack(seq_high, seq_low)  // 使用大端序
  calculated_mic = HMAC-SHA256(key, header_byte + seq_bytes + encrypted)
  mic_to_use = calculated_mic[0:4]     // 取前 4 字节
  
  if mic_to_use != mic_received:
    return ERROR("MIC verification failed, packet corrupted")

步骤 4: 解密
  plaintext = AES-128-ECB.decrypt(key, pad_to_16bytes(encrypted))
  payload = plaintext[0:5]      // 取前 5 字节

步骤 5: 解析应用层数据
  seq_id = (seq_high << 8) | seq_low  // 大端序合并
  
  temp_raw = (payload[0] << 8) | payload[1]  // int16_t, 有符号
  temp_celsius = temp_raw / 100.0
  
  humidity_percent = payload[2]
  battery_percent = payload[3]
  status_code = payload[4]
  
  timestamp = current_server_time()  // RFC3339 格式

步骤 6: 返回结构化数据
  见下方 JSON 示例
```

### 3.2 伪代码实现

```python
import hmac
import hashlib
from Crypto.Cipher import AES
import struct

def process_lora_packet(raw_data: bytes, shared_key: bytes) -> dict:
    """
    处理接收到的 LoRa 数据包
    
    Args:
        raw_data: 12 字节原始数据
        shared_key: 预共享密钥 (16 bytes, AES-128)
    
    Returns:
        解析后的应用层数据 (dict) 或 错误信息
    """
    
    # ===== 步骤 1: 包长检查 =====
    if len(raw_data) != 12:
        raise ValueError(f"Invalid packet length: {len(raw_data)}, expected 12")
    
    # ===== 步骤 2: 字节分割 =====
    header = raw_data[0]
    seq_bytes = raw_data[1:3]
    encrypted_payload = raw_data[3:8]
    mic_received = raw_data[8:12]
    
    # ===== 步骤 3: MIC 验证 =====
    data_to_verify = bytes([header]) + seq_bytes + encrypted_payload
    computed_mic = hmac.new(
        shared_key,
        data_to_verify,
        hashlib.sha256
    ).digest()[:4]
    
    if computed_mic != mic_received:
        raise ValueError("MIC verification failed - packet may be corrupted")
    
    # ===== 步骤 4: 解密 =====
    # 将 5 字节填充到 16 字节（AES 块大小）
    padding_len = 16 - (len(encrypted_payload) % 16)
    padded = encrypted_payload + bytes([padding_len] * padding_len)
    
    cipher = AES.new(shared_key, AES.MODE_ECB)
    plaintext_padded = cipher.decrypt(padded)
    plaintext_payload = plaintext_padded[:5]  # 取前 5 字节
    
    # ===== 步骤 5: 应用层数据解析 =====
    seq_id = struct.unpack('>H', seq_bytes)[0]  # 大端序 uint16
    
    # 温度：int16_t, 有符号
    temp_raw = struct.unpack('>h', plaintext_payload[0:2])[0]
    temperature = temp_raw / 100.0
    
    # 湿度、电量、状态
    humidity = plaintext_payload[2]
    battery = plaintext_payload[3]
    status_code = plaintext_payload[4]
    
    # 获取当前时间戳
    from datetime import datetime
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    # ===== 步骤 6: 返回结构化数据 =====
    return {
        "meta": {
            "protocol_version": f"0x{header:02X}",
            "sequence_id": seq_id,
            "packet_size": 12
        },
        "data": {
            "temperature": temperature,
            "humidity": humidity,
            "battery_level": battery,
            "status": {
                "code": status_code,
                "description": _get_status_description(status_code)
            }
        },
        "timestamp": timestamp
    }

def _get_status_description(code: int) -> str:
    """根据状态码返回描述"""
    status_map = {
        0: "Normal",
        1: "Fault",
        2: "Low Battery",
        3: "Sensor Error"
    }
    return status_map.get(code, "Unknown")
```

---

## 4. 应用层数据格式 (Application Layer)

### 最终 JSON 格式

后端接收和处理完成后，应该存储或推送以下 JSON 结构：

```json
{
  "meta": {
    "protocol_version": "0x11",
    "sequence_id": 1,
    "packet_size": 12
  },
  "data": {
    "temperature": 25.65,
    "humidity": 60,
    "battery_level": 95,
    "status": {
      "code": 0,
      "description": "Normal"
    }
  },
  "timestamp": "2023-10-27T10:00:00Z"
}
```

### JSON 字段说明

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| `meta.protocol_version` | string | 协议版本（固定 `0x11`） |
| `meta.sequence_id` | int | 包序号（0-65535），用于重放保护和包顺序检验 |
| `meta.packet_size` | int | 包大小（固定 12） |
| `data.temperature` | float | 温度，单位℃，小数点后两位 |
| `data.humidity` | int | 湿度，单位%，范围 0-100 |
| `data.battery_level` | int | 电量百分比，范围 0-100 |
| `data.status.code` | int | 设备状态码：0=正常, 1=故障, ... |
| `data.status.description` | string | 状态码对应描述 |
| `timestamp` | string | 后端接收时的 UTC 时间戳（RFC3339 格式） |

---

## 5. 加密与校验方案

### 5.1 密钥管理

- **AES-128 密钥**：长度固定 16 字节，需按安全方式与前端共享
  - 示例（仅用于开发测试）：`ThisIsA128BitKey`
  - 生产环境建议使用密钥管理服务（KMS）

### 5.2 加密算法

- **算法**：AES-128-ECB
- **密钥长度**：128 bit (16 bytes)
- **模式**：ECB（Electronic Code Book）
- **填充方案**：PKCS7（填充到 16 字节）

### 5.3 完整性校验

- **算法**：HMAC-SHA256
- **密钥**：同 AES 密钥
- **输入**：Header + Sequence Bytes + Encrypted Payload
- **输出**：取 SHA256 摘要的前 4 字节作为 MIC

---

## 6. 错误处理与边界情况

### 6.1 包长验证

```python
if len(packet) != 12:
    raise PacketError("Packet length mismatch")
```

### 6.2 MIC 校验失败

- 表示包在传输中被篡改或损坏
- 丢弃该包，等待下一包
- 建议记录日志用于诊断

```python
if computed_mic != received_mic:
    logger.warning(f"MIC mismatch for sequence {seq_id}")
    return None  # 丢弃
```

### 6.3 重放攻击防护

- 序号应单调递增，可检测重复包
- 建议后端维护最后接收的序号，拒绝 seq_id <= last_seq_id 的包

```python
if seq_id <= last_received_sequence:
    raise SecurityError("Replay attack detected")
last_received_sequence = seq_id
```

### 6.4 有符号温度支持

温度为 `int16_t`（有符号整数），支持负温度

```
示例：
  0xFF38 (十六进制) = -200 (十进制) ──> -2.00℃
  0x0000 (十六进制) = 0    (十进制) ──>  0.00℃
  0x0A05 (十六进制) = 2565 (十进制) ──> 25.65℃
```

---

## 7. 多个场景示例

### 场景 1：标准环境

| 字段 | 值 |
|------|-----|
| 温度 | 25.65℃ |
| 湿度 | 60% |
| 电量 | 95% |
| 状态 | 0 (正常) |
| 序号 | 1 |

**原始十六进制**：
```
11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4
```

**解密后明文**：
```
0A 05 3C 5F 00
```

---

### 场景 2：低温环境

| 字段 | 值 |
|------|-----|
| 温度 | -2.00℃ |
| 湿度 | 45% |
| 电量 | 30% |
| 状态 | 0 (正常) |
| 序号 | 2 |

**说明**：
- 温度的 int16 表示：`-200` ──> 十六进制 `0xFF38`
- 湿度：`45` ──> 十六进制 `0x2D`
- 电量：`30` ──> 十六进制 `0x1E`
- 状态：`0` ──> 十六进制 `0x00`

---

### 场景 3：异常状态

| 字段 | 值 |
|------|-----|
| 温度 | 30.80℃ |
| 湿度 | 70% |
| 电量 | 10% |
| 状态 | 1 (故障) |
| 序号 | 3 |

---

## 8. 实现检查清单

### 后端需要实现的功能

- [ ] 从串口/网络源读取 12 字节数据
- [ ] 验证包长度 == 12
- [ ] 提取 Header、Sequence、Encrypted Payload、MIC 四部分
- [ ] 使用 HMAC-SHA256 验证 MIC（防篡改）
- [ ] 拒绝 MIC 校验失败的包
- [ ] 使用 AES-128-ECB 解密 Payload
- [ ] 解析应用层数据（温度、湿度、电量、状态）
- [ ] 检测重放攻击（序号单调递增）
- [ ] 生成时间戳（后端接收时刻）
- [ ] 构建 JSON 响应
- [ ] 存库或推送到前端

---

## 9. 测试建议

### 单元测试用例

1. **MIC 校验**：发送正确的包，验证不被拒绝; 篡改一个字节，验证被拒绝
2. **温度解析**：测试正温度、负温度、边界值
3. **重放检测**：相同序号的包应被拒绝
4. **包长验证**：长度 <12 或 >12 应被拒绝

---

## 10. 补充说明

### 大端序 (Big-Endian)

多字节数值采用网络字节序（高位在前）：

```
序号 0x1234 的存储方式：
  Byte[1] = 0x12  (高位)
  Byte[2] = 0x34  (低位)

读取时应使用：
  seq = (byte[1] << 8) | byte[2]
```

### 固定长度协议的优势

- 易于同步（无需长度字段）
- 快速识别包边界
- 加密和完整性校验简单

---

**文档版本**：1.0  
**最后更新**：2023-10-27  
**维护者**：IoT 团队
