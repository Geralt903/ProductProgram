# 🎯 LoRa 树莓派网关 - 完整项目总结

## 📦 项目概述

这是一个完整的 **LoRa 传感器 -> 云服务器** 的通信方案，包含：
- ✅ 传感器端数据包生成与加密
- ✅ 树莓派网关的接收与解析
- ✅ MQTT 云端上传
- ✅ 多种编程语言的后端实现参考

---

## 📁 完整文件清单

```
ProductProgram/Gateway/
│
├── 📌 LoRa 树莓派网关（核心 - 树莓派上运行）
│   ├── lora_gateway.py ........................ ⭐ 树莓派主程序（新增）
│   └── RASPBERRY_PI_SETUP.md ................. ⭐ 树莓派部署指南（新增）
│
├── 📌 LoRa 协议文档与参考
│   ├── LORA_PROTOCOL_BACKEND_GUIDE.md ......... 详细协议文档（给后端）
│   ├── LORA_QUICK_REFERENCE.py ............... 多语言实现参考
│   └── README_LORA_PROTOCOL.md ............... 项目概览
│
├── 📌 LoRa 数据包生成器（传感器端/测试）
│   └── lora_packet_simulator.py .............. 生成加密的 12 字节包
│
├── 📌 原始示例（35位数字格式）
│   ├── terminal.py ........................... 35位数字格式接收器
│   ├── serial_listener_simple.py ............ 简单串口监听
│   ├── terminal_input_sim.py ................ 终端输入模拟
│   └── terminal_latest_5s.py ................ 5秒滑动窗口版本
│
├── 📌 其他工具
│   ├── keyboard_to_mqtt.py ................... 键盘输入转 MQTT
│   ├── windows_subscriber.py ................. Windows MQTT 订阅客户端
│   ├── mock_sender.py ....................... MQTT 模拟发送器
│   └── run_keyboard_sudo.sh ................. Linux 脚本
│
└── 📁 Sentio/ ............................... STM32 嵌入式代码（传感器端）
    └── Core/, Drivers/, cmake/ ....... 固件源码
```

---

## 🔄 系统架构与数据流

```
┌─────────────────────────────────────┐
│      STM32 LoRa 传感器节点           │
│  (Sentio - 在 Sentio/ 文件夹中)     │
│   - 采集温度、湿度、电量、状态       │
│   - 加密 (AES-128) + MIC            │
│   - 输出 12 字节二进制包            │
└────────────┬────────────────────────┘
             │
    11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4
             │ (串口 9600 baud)
             ▼
┌─────────────────────────────────────┐
│    树莓派 LoRa 网关                   │
│    (lora_gateway.py - 主程序)        │
│  ✅ 接收 12 字节加密包                │
│  ✅ 验证 MIC (HMAC-SHA256)           │
│  ✅ 解密 (AES-128-ECB)               │
│  ✅ 解析应用层数据                    │
│  ✅ 通过 MQTT 发送到云               │
└────────────┬────────────────────────┘
             │
        MQTT 1883
             │
    {"meta": {...}, "data": {...}}
             │
             ▼
┌─────────────────────────────────────┐
│      云服务器 (后端)                  │
│   (AWS IoT / Aliyun / 自建)         │
│  ✅ 接收 JSON 数据                   │
│  ✅ 存入数据库                       │
│  ✅ 前端查询 & 展示                  │
└─────────────────────────────────────┘
```

---

## 🚀 核心功能说明

### 1️⃣ 传感器端：数据包生成
**文件**: `lora_packet_simulator.py`

```python
# 生成 12 字节加密的 LoRa 数据包
simulator = LoRaPacketSimulator(b'ThisIsA128BitKey')
packet = simulator.generate_packet(
    temperature=25.65,
    humidity=60,
    battery_level=95,
    status_code=0
)
# 输出: 11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4
```

### 2️⃣ 树莓派网关：接收 & 解析
**文件**: `lora_gateway.py` ⭐ **新增**

```bash
# 树莓派上运行
python3 lora_gateway.py --port /dev/ttyUSB0 --broker 20.205.107.61

# 输出:
# [RX] Seq=0001 Temp=25.65°C Humidity=60% Battery=95% Status=Normal
# [MQTT] Published 1 messages to 'lora/gateway/receiver'
```

**功能**:
- ✅ 从串口接收 12 字节加密包
- ✅ MIC 验证（HMAC-SHA256）
- ✅ AES-128-ECB 解密
- ✅ 应用层解析（温度、湿度、电量、状态）
- ✅ MQTT 发送到云服务器
- ✅ 支持模拟模式（生成虚拟数据用于测试）
- ✅ 完整的日志记录和错误处理

### 3️⃣ 后端：接收 & 处理
**文件**: `LORA_QUICK_REFERENCE.py`

```python
# Python 后端实现
parser = LoRaPacketParser(b'ThisIsA128BitKey')
result = parser.parse_packet(raw_12_bytes)
# 返回 JSON:
# {
#   "meta": {"protocol_version": "0x11", "sequence_id": 1, ...},
#   "data": {"temperature": 25.65, "humidity": 60, ...}
# }
```

---

## 📊 数据格式说明

### 传输层：12 字节二进制包

| 字节 | 内容 | 说明 |
|------|------|------|
| 0 | `0x11` | 协议头（固定） |
| 1-2 | `0x00 0x01` | 包序号（大端序，防重放） |
| 3-7 | 加密数据 | AES-128-ECB 加密后的 5 字节 payload |
| 8-11 | `0xF1 0xE2 0xD3 0xC4` | MIC 校验码（HMAC-SHA256 前 4 字) |

**示例**:
```
11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4
^  ^  ^  ^              ^
|  |  |  |              └─ MIC (4 bytes)
|  |  |  └─ Encrypted Payload (5 bytes)
|  |  └─ Seq Low
|  └─ Seq High
└─ Header (0x11)
```

### 应用层：5 字节明文

| 偏移 | 数据类型 | 值 | 含义 |
|------|---------|-----|------|
| 0-1 | int16_t | `0x0A05` = 2565 | 温度 x100 → 25.65°C |
| 2 | uint8_t | `0x3C` = 60 | 湿度 % |
| 3 | uint8_t | `0x5F` = 95 | 电量 % |
| 4 | uint8_t | `0x00` = 0 | 状态码 (0=正常) |

### 云端：JSON 格式

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

---

## ⚡ 快速开始对照表

| 场景 | 命令 | 说明 |
|------|------|------|
| **生产** | `python3 lora_gateway.py --port /dev/ttyUSB0` | 树莓派接收真实数据 |
| **测试** | `python3 lora_gateway.py --mode simulator` | 生成虚拟数据（无串口） |
| **开发** | `python3 lora_gateway.py --mode both --broker 127.0.0.1` | 本地同时接收+模拟 |
| **生成包** | `python3 lora_packet_simulator.py` | 生成 12 字节测试包 |
| **验证协议** | 查看 `LORA_PROTOCOL_BACKEND_GUIDE.md` | 完整协议文档 |

---

## 🔐 安全性

### 加密方案
- **算法**：AES-128-ECB
- **密钥**：16 字节预共享密钥
- **密钥示例（仅限开发）**：`ThisIsA128BitKey`

### 完整性校验
- **算法**：HMAC-SHA256
- **长度**：4 字节（足以防止偶然错误和篡改）

### 重放保护
- **序号**：0-65535 单调递增
- **检测**：后端拒绝重复序号的包

---

## 📚 文件用途对应表

### 如果您想...... 请查看

| 目标 | 文件 | 何时使用 |
|------|------|---------|
| 在树莓派上部署 | `lora_gateway.py` + `RASPBERRY_PI_SETUP.md` | **生产环境** |
| 理解 LoRa 协议 | `LORA_PROTOCOL_BACKEND_GUIDE.md` | 开发/对接 |
| 测试数据包 | `lora_packet_simulator.py` | 开发/测试 |
| 后端实现参考 | `LORA_QUICK_REFERENCE.py` | 后端集成 |
| 原始示例 | `terminal.py` | 学习/参考 |
| 部署步骤 | `RASPBERRY_PI_SETUP.md` | 树莓派部署 |
| 调试窗口 | `serial_listener_simple.py` | 故障排除 |

---

## ✅ 完整实现清单

### ✨ 传感器端（STM32）
- [x] 采集温度、湿度、电量、状态
- [x] AES-128 加密处理
- [x] HMAC-SHA256 完整性校验
- [x] 12 字节包格式（固定长度）
- [x] 序号递增（防重放）

### ✨ 树莓派网关
- [x] 串口接收 12 字节包
- [x] MIC 验证（防篡改）
- [x] AES-128-ECB 解密
- [x] 应用层数据解析
- [x] MQTT 发送到云
- [x] 日志记录
- [x] 错误处理和重试
- [x] 多种运行模式（receiver/simulator/both）
- [x] 命令行参数支持
- [x] 线程安全（多线程）

### ✨ 后端支持
- [x] Python 完整实现
- [x] JavaScript/Node.js 参考代码
- [x] Java 完整实现
- [x] Go 完整实现
- [x] 详细的协议文档
- [x] 多个场景示例

---

## 🎨 代码设计特点

### 遵循 `terminal.py` 的设计模式
✅ 多线程设计（接收、处理、发送分离）  
✅ 线程安全（使用 Lock 保护共享资源）  
✅ 事件驱动（使用 stop_event 优雅关闭）  
✅ 缓冲队列（deque 缓存待发送数据）  
✅ 完整的错误处理和日志  
✅ 支持命令行参数配置  
✅ MQTT 连接重试机制  
✅ 优雅的 Ctrl+C 关闭  

---

## 📖 学习资源

### 文档
1. **协议文档**：`LORA_PROTOCOL_BACKEND_GUIDE.md` （完整协议说明）
2. **部署指南**：`RASPBERRY_PI_SETUP.md` （树莓派安装步骤）
3. **快速参考**：`LORA_QUICK_REFERENCE.py` （代码参考）
4. **项目总览**：本文件

### 代码示例
- **生成数据包**：`lora_packet_simulator.py`
- **树莓派网关**：`lora_gateway.py` ⭐
- **后端参考**：`LORA_QUICK_REFERENCE.py`
- **原始示例**：`terminal.py`

---

## 🔄 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2023-10-27 | 初始发布 |
| 1.1 | 2023-10-27 | 新增 LoRa 网关模块 |

---

## 📞 技术支持

### 常见问题

**Q: 树莓派上缺少串口权限？**  
A: 运行 `newgrp dialout` 或添加用户到 dialout 组

**Q: MQTT 连接失败？**  
A: 检查网络连接、MQTT broker 地址、防火墙

**Q: MIC 校验失败？**  
A: 确保密钥匹配、检查串口波特率、查看原始数据格式

**Q: 如何修改密钥？**  
A: 编辑 `lora_gateway.py` 中的 `SHARED_KEY` 常量

**Q: 支持多个传感器？**  
A: 支持，通过序号（sequence_id）区分，后端存库时可按序号分类

---

## 🏆 项目亮点

🔵 **完整的端到端方案**  
从传感器 → 树莓派 → 云服务器，一整套完整解决方案

🔵 **生产级代码质量**  
线程安全、错误处理、日志记录、优雅关闭

🔵 **多语言后端支持**  
Python、JavaScript/Node.js、Java、Go 均有参考实现

🔵 **详细文档**  
协议文档、部署指南、快速参考，开箱即用

🔵 **高效的树莓派设计**  
低资源占用、后台服务、支持日志轮换

🔵 **安全加密**  
AES-128 + HMAC-SHA256 + 重放保护 (Sequence Number)

---

**🎯 核心文件（树莓派）**：`lora_gateway.py` ⭐  
**📖 部署指南**：`RASPBERRY_PI_SETUP.md` ⭐  
**📋 协议文档**：`LORA_PROTOCOL_BACKEND_GUIDE.md`

---

*最后更新：2023-10-27*  
*版本：1.1*  
*适配：Raspberry Pi OS, Windows 10/11*
