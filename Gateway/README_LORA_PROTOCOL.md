# 📋 LoRa 协议实现文件清单

本目录包含 LoRa 传感器节点与后端服务器通信的完整协议实现文档和代码示例。

---

## 📁 文件清单

### 1. **lora_packet_simulator.py** 
**用途**：传感器端（前端/嵌入式）数据包生成器

- 定义了 `LoRaPacketSimulator` 类
- 实现 AES-128-ECB 加密
- 实现 HMAC-SHA256 校验码计算
- 自动生成符合协议的 12 字节数据包
- 包含多个场景示例（高温、低温、异常状态、连续多包）

**使用方式**：
```bash
python lora_packet_simulator.py
```

**输出**：生成完整的 12 字节十六进制数据包，可直接发送给后端

---

### 2. **LORA_PROTOCOL_BACKEND_GUIDE.md**
**用途**：后端开发完整参考文档

这是给后端开发人员的 **完整配置文档**，包含：

- 物理层数据格式详解
- 字节结构拆解说明
- 应用层数据定义
- 后端接收 & 处理流程（6 个步骤）
- Python 伪代码实现
- 加密与校验方案详细说明
- MIC 验证流程
- 错误处理 & 边界情况
- 多个场景示例
- 重放攻击防护方案
- 有符号温度支持说明
- 实现检查清单
- 打字序说明

**适用对象**：后端开发人员（Java、Python、Go、Node.js 等）

---

### 3. **LORA_QUICK_REFERENCE.py**
**用途**：多种编程语言的快速参考实现

包含以下语言的完整可用代码：

- **Python** ✅（最简版，复制即用）
- **JavaScript/Node.js**（部分代码示例）
- **Java**（完整类实现）
- **Go**（完整实现）

每个实现都包含：
- 完整的包解析逻辑
- MIC 验证
- AES-128 解密
- 应用层解析
- 错误处理

---

## 🔄 工作流程图

```
传感器端 (Frontend)                     后端 (Backend)
═════════════════════════════════════════════════════════

  传感器采集数据
       ↓
  [温度, 湿度, 电量, 状态]
       ↓
  Simulator.generate_packet()
       ↓
  构建明文 Payload (5 字节)
       ↓
  AES-128 加密
       ↓
  计算 HMAC-SHA256 MIC
       ↓
  [12 字节二进制包]
       ↓
  通过串口/网络发送  ──→  接收 12 字节数据
                        ↓
                   提取 Header/Seq/Encrypted/MIC
                        ↓
                   验证 MIC (HMAC-SHA256)
                        ↓
                   AES-128 解密
                        ↓
                   解析明文数据
                        ↓
                   生成 JSON 响应
                        ↓
                   存库 / 推送前端
```

---

## 🚀 快速开始

### 前端（传感器端）快速开始

```python
from lora_packet_simulator import LoRaPacketSimulator

# 创建模拟器
simulator = LoRaPacketSimulator(b'ThisIsA128BitKey')

# 生成数据包
packet = simulator.generate_packet(
    temperature=25.65,
    humidity=60,
    battery_level=95,
    status_code=0
)

# 转换为十六进制字符串发送
hex_string = simulator.packet_to_hex_string(packet)
print(f"发送: {hex_string}")
# 输出: 11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4
```

### 后端（服务器端）快速开始

#### Python 版本

```python
from LORA_QUICK_REFERENCE import LoRaPacketParser

parser = LoRaPacketParser(b'ThisIsA128BitKey')
raw_data = bytes.fromhex('1100 01A5B92D4F88F1E2D3C4')
result = parser.parse_packet(raw_data)
print(json.dumps(result, indent=2))
```

#### Node.js 版本
见 `LORA_QUICK_REFERENCE.py` 中的 JavaScript 代码段

#### Java 版本
见 `LORA_QUICK_REFERENCE.py` 中的 Java 类实现

#### Go 版本
见 `LORA_QUICK_REFERENCE.py` 中的 Go 实现

---

## 🔐 安全性说明

### 密钥管理
- **当前示例密钥**：`ThisIsA128BitKey`（仅用于开发测试）
- **生产环境**：使用安全的密钥管理服务（KMS）
- **密钥长度**：AES-128 固定 16 字节
- **密钥共享**：前后端应通过安全渠道预先共享密钥

### 防护措施
1. **MIC 校验**：HMAC-SHA256，防止包被篡改
2. **重放保护**：序号单调递增，拒绝重复包
3. **包长验证**：严格检查 12 字节，其他长度直接丢弃
4. **有符号整数**：温度支持负值（int16_t）

---

## 📊 示例数据

### 场景 1：标准环境
```
温度: 25.65°C
湿度: 60%
电量: 95%
状态: 正常

生成的 12 字节包：
11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4

解密后明文：
0A 05 3C 5F 00
```

### 场景 2：低温环境
```
温度: -2.00°C （支持负温度）
湿度: 45%
电量: 30%
状态: 正常

解密后明文：
FF 38 2D 1E 00
```

---

## ✅ 实现检查清单（给后端开发）

- [ ] 配置共享密钥（16 字节 AES-128）
- [ ] 实现 12 字节包长验证
- [ ] 实现 MIC 校验（HMAC-SHA256）
- [ ] 实现 AES-128-ECB 解密
- [ ] 实现应用层数据解析（5 字节 plaintext）
- [ ] 实现序号防重放检查
- [ ] 实现有符号温度解析（int16_t）
- [ ] 生成 JSON 响应
- [ ] 存库或推送到前端
- [ ] 单元测试（测试 MIC 失败、包长不对、重放等）
- [ ] 错误日志记录

---

## 🧪 测试建议

### 单元测试用例

1. **篡改测试**
   - 修改任意一个字节，验证 MIC 校验失败

2. **重放测试**
   - 发送相同序号的包，验证被拒绝

3. **长度测试**
   - 发送 11 字节或 13 字节的包，验证被拒绝

4. **负温度测试**
   - 发送 0xFF38（-200 dec = -2.00°C），验证正确解析

5. **边界测试**
   - 最高温度、最低电量、最大湿度等

---

## 📞 技术支持

### 常见问题

**Q1: 为什么使用 ECB 模式而不是 CBC？**
- 原因：5 字节的固定长度 payload，填充到 16 字节后，ECB 足够，且实现简 单。

**Q2: 密钥如何安全地共享给后端？**
- 建议：使用密钥管理服务（KMS），或通过安全通道（如 HTTPS + 密钥协商协议）预先配置。

**Q3: MIC 为什么只取 4 字节而不是全部 32 字节？**
- 原因：权衡安全性与包大小，4 字节（32 bit）足以防止偶然错误和大部分篡改。

**Q4: 如果接收到格式错误的包怎么办？**
- 建议：记录日志、计数器递增，但直接丢弃该包，等待下一个正常包。

---

## 📚 相关资源

- **AES-128-ECB**：NIST FIPS 197（Advanced Encryption Standard）
- **HMAC-SHA256**：RFC 2104 + SHA256（FIPS 180-4）
- **大端序**：RFC 791（网络字节序）

---

## 🔄 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2023-10-27 | 初始版本 |

---

## 📝 使用许可

这些代码示例和文档仅供参考和学习用途。  
在生产环境中使用前，请进行充分的安全审查和测试。

---

**最后更新**：2023-10-27  
**维护者**：IoT 团队
