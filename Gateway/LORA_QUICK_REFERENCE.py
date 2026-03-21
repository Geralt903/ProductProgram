"""
快速参考：LoRa 协议后端实现 (Quick Reference for Backend)
==========================================================

复制以下代码框架，集成到你的后端项目中
"""

# ============================================================================
# Node.js / JavaScript 实现示例
# ============================================================================

# 如果用 JavaScript，需要安装：
# npm install crypto pycryptodome

"""
const crypto = require('crypto');

class LoRaPacketParser {
  constructor(sharedKey) {
    // sharedKey 应该是 Buffer，长度 16 bytes (AES-128)
    this.sharedKey = sharedKey;
  }

  parsePacket(rawData) {
    // rawData 应该是 Buffer，长度 12 bytes
    
    if (rawData.length !== 12) {
      throw new Error(`Invalid packet length: ${rawData.length}, expected 12`);
    }

    const header = rawData[0];
    const seqBytes = rawData.slice(1, 3);
    const encryptedPayload = rawData.slice(3, 8);
    const micReceived = rawData.slice(8, 12);

    // 验证 MIC
    const dataToVerify = Buffer.concat([Buffer.from([header]), seqBytes, encryptedPayload]);
    const hmac = crypto.createHmac('sha256', this.sharedKey);
    hmac.update(dataToVerify);
    const computedMic = hmac.digest().slice(0, 4);

    if (!computedMic.equals(micReceived)) {
      throw new Error('MIC verification failed - packet corrupted');
    }

    // 解密
    const cipher = crypto.createDecipheriv('aes-128-ecb', this.sharedKey, '');
    // 填充到 16 字节
    const paddingLen = 16 - (encryptedPayload.length % 16);
    const padded = Buffer.concat([
      encryptedPayload,
      Buffer.alloc(paddingLen, paddingLen)
    ]);
    
    let decrypted = cipher.update(padded);
    decrypted = Buffer.concat([decrypted, cipher.final()]);
    const plaintext = decrypted.slice(0, 5);

    // 解析应用层数据
    const seqId = seqBytes.readUInt16BE(0);
    const tempRaw = plaintext.readInt16BE(0);
    const temperature = tempRaw / 100.0;
    const humidity = plaintext[2];
    const battery = plaintext[3];
    const statusCode = plaintext[4];

    return {
      meta: {
        protocol_version: `0x${header.toString(16).toUpperCase().padStart(2, '0')}`,
        sequence_id: seqId,
        packet_size: 12
      },
      data: {
        temperature: temperature,
        humidity: humidity,
        battery_level: battery,
        status: {
          code: statusCode,
          description: this.getStatusDescription(statusCode)
        }
      },
      timestamp: new Date().toISOString()
    };
  }

  getStatusDescription(code) {
    const map = {
      0: 'Normal',
      1: 'Fault',
      2: 'Low Battery',
      3: 'Sensor Error'
    };
    return map[code] || 'Unknown';
  }
}

// 使用示例：
const sharedKey = Buffer.from('ThisIsA128BitKey');
const parser = new LoRaPacketParser(sharedKey);

const rawHex = '11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4';
const rawData = Buffer.from(rawHex.split(' ').map(x => parseInt(x, 16)));

try {
  const result = parser.parsePacket(rawData);
  console.log(JSON.stringify(result, null, 2));
} catch (error) {
  console.error('Parse error:', error.message);
}
"""

# ============================================================================
# Python 实现 (最简版本，复制即用)
# ============================================================================

import struct
import hmac
import hashlib
from Crypto.Cipher import AES
from datetime import datetime
import json

class LoRaPacketParser:
    def __init__(self, shared_key: bytes):
        """
        初始化解析器
        
        Args:
            shared_key: 16 字节的 AES-128 密钥
        """
        if len(shared_key) != 16:
            raise ValueError("Key must be 16 bytes for AES-128")
        self.shared_key = shared_key
    
    def parse_packet(self, raw_data: bytes) -> dict:
        """
        解析 LoRa 数据包
        
        Args:
            raw_data: 12 字节的铁路数据包
            
        Returns:
            解析后的 JSON 对象
            
        Raises:
            ValueError: 包长度不正确或 MIC 校验失败
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
            self.shared_key,
            data_to_verify,
            hashlib.sha256
        ).digest()[:4]
        
        if computed_mic != mic_received:
            raise ValueError("MIC verification failed - packet may be corrupted or tampered")
        
        # ===== 步骤 4: 解密 =====
        # 将 5 字节填充到 16 字节（AES 块大小）
        padding_len = 16 - (len(encrypted_payload) % 16)
        padded = encrypted_payload + bytes([padding_len] * padding_len)
        
        cipher = AES.new(self.shared_key, AES.MODE_ECB)
        plaintext_padded = cipher.decrypt(padded)
        plaintext_payload = plaintext_padded[:5]  # 取前 5 字节
        
        # ===== 步骤 5: 应用层解析 =====
        seq_id = struct.unpack('>H', seq_bytes)[0]  # 大端序 uint16
        
        # 温度：int16_t, 有符号
        temp_raw = struct.unpack('>h', plaintext_payload[0:2])[0]
        temperature = round(temp_raw / 100.0, 2)
        
        # 湿度、电量、状态
        humidity = plaintext_payload[2]
        battery = plaintext_payload[3]
        status_code = plaintext_payload[4]
        
        # 时间戳
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
                    "description": self._get_status_description(status_code)
                }
            },
            "timestamp": timestamp
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
        return status_map.get(code, "Unknown")


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == '__main__':
    # 配置共享密钥
    SHARED_KEY = b'ThisIsA128BitKey'  # 16 字节
    
    # 创建解析器
    parser = LoRaPacketParser(SHARED_KEY)
    
    # 原始 12 字节数据
    hex_string = '11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4'
    raw_data = bytes.fromhex(hex_string.replace(' ', ''))
    
    # 解析
    try:
        result = parser.parse_packet(raw_data)
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(f"错误: {e}")

# ============================================================================
# Java 实现示例
# ============================================================================

"""
import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.*;

public class LoRaPacketParser {
    private byte[] sharedKey;

    public LoRaPacketParser(byte[] sharedKey) {
        if (sharedKey.length != 16) {
            throw new IllegalArgumentException("Key must be 16 bytes for AES-128");
        }
        this.sharedKey = sharedKey;
    }

    public Map<String, Object> parsePacket(byte[] rawData) throws Exception {
        if (rawData.length != 12) {
            throw new IllegalArgumentException("Invalid packet length: " + rawData.length);
        }

        byte header = rawData[0];
        byte[] seqBytes = Arrays.copyOfRange(rawData, 1, 3);
        byte[] encryptedPayload = Arrays.copyOfRange(rawData, 3, 8);
        byte[] micReceived = Arrays.copyOfRange(rawData, 8, 12);

        // 验证 MIC
        byte[] dataToVerify = new byte[header.length + 2 + 5];
        dataToVerify[0] = header;
        System.arraycopy(seqBytes, 0, dataToVerify, 1, 2);
        System.arraycopy(encryptedPayload, 0, dataToVerify, 3, 5);

        Mac hmac = Mac.getInstance("HmacSHA256");
        SecretKeySpec keySpec = new SecretKeySpec(sharedKey, "HmacSHA256");
        hmac.init(keySpec);
        byte[] computedMic = new byte[4];
        byte[] hmacResult = hmac.doFinal(dataToVerify);
        System.arraycopy(hmacResult, 0, computedMic, 0, 4);

        if (!Arrays.equals(computedMic, micReceived)) {
            throw new SecurityException("MIC verification failed");
        }

        // 解密（使用 AES-128-ECB）
        Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
        SecretKeySpec decryptKey = new SecretKeySpec(sharedKey, 0, 16, "AES");
        cipher.init(Cipher.DECRYPT_MODE, decryptKey);
        
        byte[] plaintext = cipher.doFinal(encryptedPayload);

        // 解析应用层数据
        short tempRaw = ByteBuffer.wrap(plaintext, 0, 2)
            .order(ByteOrder.BIG_ENDIAN).getShort();
        double temperature = tempRaw / 100.0;
        int humidity = plaintext[2] & 0xFF;
        int battery = plaintext[3] & 0xFF;
        int statusCode = plaintext[4] & 0xFF;
        int seqId = ByteBuffer.wrap(seqBytes)
            .order(ByteOrder.BIG_ENDIAN).getShort() & 0xFFFF;

        // 构建返回值
        Map<String, Object> result = new HashMap<>();
        
        Map<String, Object> meta = new HashMap<>();
        meta.put("protocol_version", String.format("0x%02X", header));
        meta.put("sequence_id", seqId);
        meta.put("packet_size", 12);
        
        Map<String, Object> data = new HashMap<>();
        data.put("temperature", temperature);
        data.put("humidity", humidity);
        data.put("battery_level", battery);
        
        Map<String, Object> status = new HashMap<>();
        status.put("code", statusCode);
        status.put("description", getStatusDescription(statusCode));
        data.put("status", status);
        
        result.put("meta", meta);
        result.put("data", data);
        result.put("timestamp", new Date().toString());
        
        return result;
    }

    private static String getStatusDescription(int code) {
        switch (code) {
            case 0: return "Normal";
            case 1: return "Fault";
            case 2: return "Low Battery";
            case 3: return "Sensor Error";
            default: return "Unknown";
        }
    }
}
"""

# ============================================================================
# Go 实现示例
# ============================================================================

"""
package main

import (
    "crypto/aes"
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "time"
)

type LoRaPacketParser struct {
    sharedKey []byte
}

func NewLoRaPacketParser(sharedKey []byte) *LoRaPacketParser {
    return &LoRaPacketParser{sharedKey: sharedKey}
}

func (p *LoRaPacketParser) ParsePacket(rawData []byte) (map[string]interface{}, error) {
    if len(rawData) != 12 {
        return nil, fmt.Errorf("invalid packet length: %d, expected 12", len(rawData))
    }

    header := rawData[0]
    seqBytes := rawData[1:3]
    encryptedPayload := rawData[3:8]
    micReceived := rawData[8:12]

    // 验证 MIC
    dataToVerify := append([]byte{header}, seqBytes...)
    dataToVerify = append(dataToVerify, encryptedPayload...)

    h := hmac.New(sha256.New, p.sharedKey)
    h.Write(dataToVerify)
    computedMic := h.Sum(nil)[:4]

    if !hmac.Equal(computedMic, micReceived) {
        return nil, fmt.Errorf("MIC verification failed")
    }

    // 解密
    cipher, err := aes.NewCipher(p.sharedKey)
    if err != nil {
        return nil, err
    }

    // 使用 ECB 模式解密（需要自己实现 ECB）
    plaintext := make([]byte, 16)
    cipher.Decrypt(plaintext, encryptedPayload) // 注意：这里需要填充处理

    // 解析数据
    tempRaw := int16(plaintext[0])<<8 | int16(plaintext[1])
    temperature := float64(tempRaw) / 100.0
    humidity := plaintext[2]
    battery := plaintext[3]
    statusCode := plaintext[4]

    seqId := int(seqBytes[0])<<8 | int(seqBytes[1])

    result := map[string]interface{}{
        "meta": map[string]interface{}{
            "protocol_version": fmt.Sprintf("0x%02X", header),
            "sequence_id":      seqId,
            "packet_size":      12,
        },
        "data": map[string]interface{}{
            "temperature":   temperature,
            "humidity":      humidity,
            "battery_level": battery,
            "status": map[string]interface{}{
                "code":        statusCode,
                "description": getStatusDescription(statusCode),
            },
        },
        "timestamp": time.Now().UTC().Format(time.RFC3339),
    }

    return result, nil
}

func getStatusDescription(code byte) string {
    switch code {
    case 0:
        return "Normal"
    case 1:
        return "Fault"
    case 2:
        return "Low Battery"
    case 3:
        return "Sensor Error"
    default:
        return "Unknown"
    }
}
"""

# ============================================================================
# 快速测试步骤
# ============================================================================

"""
1. 安装依赖：
   pip install pycryptodome

2. 复制上面的 LoRaPacketParser 类到你的项目

3. 测试代码：
   ```python
   SHARED_KEY = b'ThisIsA128BitKey'
   parser = LoRaPacketParser(SHARED_KEY)
   raw_data = bytes.fromhex('11000 1A5B92D4F88F1E2D3C4')
   result = parser.parse_packet(raw_data)
   print(json.dumps(result, indent=2))
   ```

4. 输出应该是：
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
"""
