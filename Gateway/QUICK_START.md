# 🎯 快速导航 - LoRa 树莓派网关项目

## 👋 第一次来？从这里开始！

### 1️⃣ **理解项目结构** (5 分钟)
📖 [项目总览](PROJECT_OVERVIEW.md)
- 了解系统架构
- 看数据流向
- 掌握核心概念

### 2️⃣ **了解 LoRa 协议** (10 分钟)
📚 [LoRa 协议详解](LORA_PROTOCOL_BACKEND_GUIDE.md)
- 12 字节包格式
- 加密与校验方式
- 应用层数据定义
- 错误处理方法

### 3️⃣ **在树莓派上部署** (30 分钟)
🚀 [树莓派部署指南](RASPBERRY_PI_SETUP.md)
- 安装依赖库
- 检查串口配置
- 运行网关程序
- 排查故障问题

### 4️⃣ **集成到您的后端** (1 小时)
💻 [快速参考](LORA_QUICK_REFERENCE.py)
- Python 实现
- Java 实现
- Node.js 实现
- Go 实现

---

## 📊 按场景查找

### 🎓 我是学生/初学者
1. 阅读 [项目总览](PROJECT_OVERVIEW.md) 的 "系统架构及数据流" 部分
2. 查看 [LoRa 协议详解](LORA_PROTOCOL_BACKEND_GUIDE.md) 的示例
3. 运行 `python3 lora_packet_simulator.py` 看生成的数据包
4. 查看 [快速参考](LORA_QUICK_REFERENCE.py) 中的代码实现

### 🔧 我是树莓派系统管理员
1. 按照 [树莓派部署指南](RASPBERRY_PI_SETUP.md) 的第 1-3 步安装
2. 运行 `python3 lora_gateway.py --port /dev/ttyUSB0`
3. 查看日志文件 `lora_gateway.log`
4. 配置后台服务（见部署指南的"部署建议"部分）

### 💡 我是后端开发人员
1. 查看 [LoRa 协议详解](LORA_PROTOCOL_BACKEND_GUIDE.md) 的"后端接收与处理逻辑"部分
2. 选择您使用的语言，参考 [快速参考](LORA_QUICK_REFERENCE.py)
3. 将 `LoRaPacketParser` 集成到您的项目
4. 测试：使用 `lora_gateway.py` 的模拟模式 (`--mode simulator`)

### 🧪 我想做单元测试
1. 使用 `lora_packet_simulator.py` 生成测试数据
2. 运行 `lora_gateway.py --mode simulator --broker 127.0.0.1`
3. 订阅 MQTT 主题验证数据格式
4. 参考 [部署指南](RASPBERRY_PI_SETUP.md) 的"测试步骤"

### 🔐 我需要修改密钥/参数
编辑 `lora_gateway.py` 中的常量：
```python
SHARED_KEY = b'YourNewKeyHere!!'  # 16 字节
MQTT_TOPIC_RECEIVER = "your/new/topic"
DEFAULT_SERIAL_PORT = "/dev/ttyACM0"
```

---

## 📁 文件导航

### 🏆 核心文件（优先查看）

| 文件 | 描述 | 行数 | 跳转 |
|------|------|------|------|
| **lora_gateway.py** | 树莓派主程序⭐ | ~680 | 直接运行 |
| **RASPBERRY_PI_SETUP.md** | 部署指南⭐ | - | 按步骤走 |
| **LORA_PROTOCOL_BACKEND_GUIDE.md** | 协议完全文档 | - | 学习协议 |
| **PROJECT_OVERVIEW.md** | 项目总览 | - | 了解全貌 |

### 📚 参考文件（需要时查看）

| 文件 | 描述 | 用途 |
|------|------|------|
| **LORA_QUICK_REFERENCE.py** | 多语言实现参考 | 后端集成 |
| **lora_packet_simulator.py** | 数据包生成器 | 生成测试数据 |
| **terminal.py** | 原始示例（35位） | 学习设计模式 |
| **serial_listener_simple.py** | 串口监听 | 调试串口 |

---

## 🚀 三条快速赛道

### 🏁 赛道 A: 仅树莓派部署（30 分钟）
```bash
# 1. 安装依赖
pip install pyserial paho-mqtt pycryptodome

# 2. 检查串口
ls /dev/tty*

# 3. 直接运行
python3 lora_gateway.py --port /dev/ttyUSB0

# 4. 查看输出
# [RX] Seq=0001 Temp=25.65°C Humidity=60% ...
```

### 🏁 赛道 B: 本地测试（20 分钟）
```bash
# 1. 安装依赖
pip install pycryptodome

# 2. 生成测试数据
python3 lora_packet_simulator.py

# 3. 查看数据包
# 11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4

# 4. 模拟网关接收
python3 lora_gateway.py --mode simulator
```

### 🏁 赛道 C: 集成后端（1 小时）
```python
# 1. 从 LORA_QUICK_REFERENCE.py 复制 LoRaPacketParser 类
# 2. 初始化解析器
parser = LoRaPacketParser(b'ThisIsA128BitKey')

# 3. 接收数据并解析
result = parser.parse_packet(raw_12_bytes)

# 4. 获得结构化 JSON
print(result['data']['temperature'])  # 25.65
```

---

## 🔍 按文件格式查找

### 📝 Markdown 文档 (.md)
- 📖 [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - 项目总览 ⭐
- 📖 [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md) - 部署指南 ⭐
- 📖 [LORA_PROTOCOL_BACKEND_GUIDE.md](LORA_PROTOCOL_BACKEND_GUIDE.md) - 协议文档
- 📖 [README_LORA_PROTOCOL.md](README_LORA_PROTOCOL.md) - LoRa 概览

### 🐍 Python 代码 (.py)
- **🟢 lora_gateway.py** - 树莓派主程序（新增）
- **🟢 lora_packet_simulator.py** - 包生成器
- **🟢 LORA_QUICK_REFERENCE.py** - 参考实现
- **🔵 terminal.py** - 原始示例

### 🛠️ 配置/脚本 (.sh, .cfg 等)
- run_keyboard_sudo.sh - Linux 脚本
- stm32f103c8_blue_pill.cfg - STM32 配置

---

## ⏱️ 时间表

### 实施总时间：2-3 小时

| 步骤 | 时间 | 工作 |
|------|------|------|
| 1. 理解协议 | 20 min | 阅读文档 |
| 2. 准备环境 | 15 min | 安装依赖 |
| 3. 本地测试 | 20 min | 生成/解析数据包 |
| 4. 树莓派部署 | 30 min | 安装 + 运行 |
| 5. 后端集成 | 40 min | 集成到后端 |
| 6. 测试验证 | 20 min | 端到端测试 |

---

## 🎯 检查清单

从上到下完成：

- [ ] 下载/查看 [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) （5 min）
- [ ] 阅读 [LORA_PROTOCOL_BACKEND_GUIDE.md](LORA_PROTOCOL_BACKEND_GUIDE.md) 前 3 章 （20 min）
- [ ] 在本地运行 `lora_packet_simulator.py`（10 min）
- [ ] 根据 [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md) 安装树莓派环境（30 min）
- [ ] 在树莓派运行 `python3 lora_gateway.py --mode simulator`（10 min）
- [ ] 在树莓派运行 `python3 lora_gateway.py --port /dev/ttyUSB0`（实际接收）（5 min）
- [ ] 根据 [LORA_QUICK_REFERENCE.py](LORA_QUICK_REFERENCE.py) 集成后端（60 min）
- [ ] 端到端测试验证（20 min）

---

## 💡 关键概念快速参考

| 概念 | 说明 | 详见 |
|------|------|------|
| **12 字节包** | Header(1) + Seq(2) + Encrypted(5) + MIC(4) | 协议文档 §1 |
| **AES-128** | 加密算法，16 字节密钥，ECB 模式 | 协议文档 §5 |
| **HMAC-SHA256** | 完整性校验，防篡改，取前 4 字节 | 协议文档 §5 |
| **序号(Sequence)** | 0-65535，单调递增，防重放 | 协议文档 §6.3 |
| **模拟器模式** | 生成虚拟数据，用于测试（无串口） | 部署指南 §3 |
| **MQTT Topic** | `lora/gateway/receiver` 和 `simulator` | 网关代码 |
| **JSON 响应** | 包含温度、湿度、电量、状态等 | 协议文档 §4 |

---

## 🆘 遇到问题？

### 问题 1: "找不到串口"
👉 查看 [部署指南 §1](RASPBERRY_PI_SETUP.md#问题-1找不到串口)

### 问题 2: "MQTT 连接失败"
👉 查看 [部署指南 §2](RASPBERRY_PI_SETUP.md#问题-2mqtt-连接失败)

### 问题 3: "MIC 校验失败"
👉 查看 [协议文档 §6.2](LORA_PROTOCOL_BACKEND_GUIDE.md#62-mic-校验失败)

### 问题 4: "权限被拒绝"
👉 查看 [部署指南第 2 步](RASPBERRY_PI_SETUP.md#赋予串口访问权限)

### 问题 5: "缺少库"
👉 查看 [部署指南第 1 步](RASPBERRY_PI_SETUP.md#第-1-步安装依赖)

---

## 📞 快速链接

| 需要 | 链接 |
|------|------|
| **项目整体了解** | [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) |
| **树莓派部署** | [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md) |
| **LoRa 协议细节** | [LORA_PROTOCOL_BACKEND_GUIDE.md](LORA_PROTOCOL_BACKEND_GUIDE.md) |
| **后端代码参考** | [LORA_QUICK_REFERENCE.py](LORA_QUICK_REFERENCE.py) |
| **生成测试数据** | [lora_packet_simulator.py](lora_packet_simulator.py) |
| **树莓派主程序** | [lora_gateway.py](lora_gateway.py) |

---

## 🎓 学习路径建议

### 初级（完全新手）
1. 阅读 [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - 了解整体
2. 看 [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md) 的快速开始部分
3. 运行 `lora_packet_simulator.py` 看生成的数据

### 中级（有 IoT/嵌入式基础）
1. 深入阅读 [LORA_PROTOCOL_BACKEND_GUIDE.md](LORA_PROTOCOL_BACKEND_GUIDE.md)
2. 按 [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md) 完整部署
3. 查看 `lora_gateway.py` 源码，理解多线程设计

### 高级（后端开发人员）
1. 快速查看协议格式（[协议文档 §1-2](LORA_PROTOCOL_BACKEND_GUIDE.md#1-物理层数据格式)）
2. 使用 [LORA_QUICK_REFERENCE.py](LORA_QUICK_REFERENCE.py) 对应语言的实现
3. 集成到您的后端服务

---

## 🔗 外部资源

- **树莓派官方**: https://www.raspberrypi.org/
- **MQTT 协议**: https://mqtt.org/
- **AES 加密**: NIST FIPS 197
- **Python Serial**: https://pyserial.readthedocs.io/

---

**👉 建议：按照上面的"快速赛道"选择您要走的路，然后依次查看对应文件！**

**⏱️ 预计总时间：2-3 小时从零到部署**

**✅ 目标：树莓派上运行稳定的 LoRa 网关，数据上传到云服务器**

---

*快速导航版本：1.0*  
*最后更新：2023-10-27*

```
┌─────────────────────────────────────────┐
│  🎯 从这里开始：阅读 PROJECT_OVERVIEW.md  │
│  然后按照 RASPBERRY_PI_SETUP.md 部署     │
│  遇到问题查看相应部分                     │
└─────────────────────────────────────────┘
```
