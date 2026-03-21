# 树莓派 LoRa 网关快速部署指南

## 📋 文件清单

```
ProductProgram/Gateway/
├── lora_gateway.py              # 这是树莓派上运行的主程序 ✅ 新增
├── lora_packet_simulator.py     # 传感器端数据包生成器
├── LORA_QUICK_REFERENCE.py      # 多语言参考实现
├── LORA_PROTOCOL_BACKEND_GUIDE.md  # 完整协议文档
├── terminal.py                  # 原始示例（35位数字包）
├── serial_listener_simple.py    # 串口监听示例
└── run_keyboard_sudo.sh         # Linux 脚本（参考）
```

---

## 🚀 快速开始

### 第 1 步：安装依赖

#### 树莓派（Raspberry Pi OS）

```bash
# 更新系统
sudo apt-get update
sudo apt-get upgrade

# 安装 Python3 和 pip
sudo apt-get install python3 python3-pip

# 安装必要的库
pip install pyserial paho-mqtt pycryptodome

# 验证安装
python3 -c "import serial, paho.mqtt.client, Crypto; print('All dependencies OK')"
```

#### Windows（测试用）

```bash
pip install pyserial paho-mqtt pycryptodome
```

---

### 第 2 步：检查串口设置

#### 树莓派上查找 LoRa 模块

```bash
# 列出所有 USB 设备
ls -la /dev/tty*

# 通常是以下之一：
# /dev/ttyUSB0   (USB 转串口)
# /dev/ttyACM0   (Arduino/STM32)
# /dev/ttyS0     (内置串口)

# 也可以使用
dmesg | grep tty
```

#### 赋予串口访问权限

```bash
# 添加 pi 用户到 dialout 组
sudo usermod -a -G dialout pi

# 重新登录或使用 newgrp
newgrp dialout

# 验证权限
ls -l /dev/ttyUSB0
```

---

### 第 3 步：运行 LoRa 网关

#### 模式 1：接收串口数据（生产模式）

```bash
# 在树莓派上运行
python3 lora_gateway.py --port /dev/ttyUSB0 --baud 9600 --broker 20.205.107.61

# 或使用默认值（如果 /dev/ttyUSB0 是正确的端口）
python3 lora_gateway.py
```

**输出示例：**
```
======================================================================
树莓派 LoRa 网关 - Raspberry Pi LoRa Gateway
======================================================================
[CONFIG] Mode: receiver
[CONFIG] MQTT Broker: 20.205.107.61:1883
[CONFIG] Log file: lora_gateway.log
[INFO] Opening serial port: /dev/ttyUSB0 @ 9600 baud
[OK] Serial port connected
[INFO] MQTT connection attempt 1/3...
[OK] MQTT connected successfully!
[INFO] All threads started, press Ctrl+C to stop

[RX] Seq=0001 Temp=25.65°C Humidity=60% Battery=95% Status=Normal
```

#### 模式 2：模拟生成测试数据

```bash
# 不需要串口，只生成虚拟数据
python3 lora_gateway.py --mode simulator

# 或在本地测试（broker 127.0.0.1）
python3 lora_gateway.py --mode simulator --broker 127.0.0.1
```

**输出示例：**
```
[SIM] Seq=0001 Temp=20.12°C Humidity=50% Battery=90% Status=Normal
[MQTT] Published 1 messages to 'lora/gateway/simulator'
```

#### 模式 3：同时接收和模拟（测试模式）

```bash
python3 lora_gateway.py --mode both --port /dev/ttyUSB0 --broker 20.205.107.61
```

---

## 📊 MQTT 数据格式

### 接收到的实际传感器数据

**Topic:** `lora/gateway/receiver`

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
  "timestamp": "2023-10-27T10:00:00Z",
  "raw_hex": "11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4"
}
```

### 模拟生成的测试数据

**Topic:** `lora/gateway/simulator`

同样格式，但来自虚拟生成器（用于测试）

---

## 🔧 参数说明

```
用法:
  python3 lora_gateway.py [OPTIONS]

选项:
  --port PORT          串口路径 (默认: /dev/ttyUSB0)
  --baud BAUD          波特率 (默认: 9600)
  --broker ADDRESS     MQTT broker 地址 (默认: 20.205.107.61)
  --mode {receiver|simulator|both}
                       运行模式:
                       - receiver:   从串口接收数据（生产）
                       - simulator:  生成虚拟数据（测试）
                       - both:       同时接收和生成（测试）

示例:
  # 树莓派生产环境
  python3 lora_gateway.py --port /dev/ttyUSB0 --broker 20.205.107.61

  # 本地测试
  python3 lora_gateway.py --mode simulator --broker 127.0.0.1

  # Windows 测试
  python3 lora_gateway.py --port COM3 --broker 127.0.0.1
```

---

## 📝 日志文件

所有事件都记录到 `lora_gateway.log`：

```
2023-10-27T10:00:00Z [RX] 11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4 -> OK
2023-10-27T10:00:05Z [SIM] 11 00 02 B6 CA 3E 50 99 G2 F3 E4 D5 -> OK
2023-10-27T10:00:10Z [RX_ERROR] 11 00 03 ... -> MIC verification failed
```

查看日志：
```bash
tail -f lora_gateway.log        # 实时查看
grep "RX" lora_gateway.log      # 只看接收记录
grep "ERROR" lora_gateway.log   # 只看错误
```

---

## 🧪 测试步骤

### 1. 测试串口连接

```bash
# 查看开放的串口
python3 -c "import serial; print(serial.tools.list_ports.comports())"

# 或使用树莓派内置工具
ls /dev/tty*
```

### 2. 测试 MQTT 连接

```bash
# 在另一个终端订阅 MQTT 主题
mosquitto_sub -h 20.205.107.61 -t "lora/gateway/+"

# 或使用 Python
python3 -c "
import paho.mqtt.client as mqtt
c = mqtt.Client()
c.connect('20.205.107.61', 1883, 60)
c.subscribe('lora/gateway/#')
c.loop_forever()
"
```

### 3. 在本地测试模拟器

```bash
# 不需要实际硬件，只测试数据格式
python3 lora_gateway.py --mode simulator --broker 127.0.0.1
```

### 4. 生成并发送测试数据包

```bash
# 使用 lora_packet_simulator.py 生成原始数据
python3 lora_packet_simulator.py

# 输出示例：
# 场景 1 标准场景 - 温度 25.65℃, 湿度 60%, 电量 95%, 正常状态
# 十六进制字符串: 11 00 01 A5 B9 2D 4F 88 F1 E2 D3 C4
```

---

## 🐛 故障排除

### 问题 1：找不到串口

```
[ERROR] Failed to open serial port /dev/ttyUSB0: [Errno 2] No such file or directory: '/dev/ttyUSB0'
```

**解决方案：**
```bash
# 1. 检查 LoRa 模块是否连接
ls /dev/tty*

# 2. 尝试其他串口
python3 lora_gateway.py --port /dev/ttyACM0

# 3. 检查权限
ls -l /dev/ttyUSB0
sudo chmod 666 /dev/ttyUSB0
```

### 问题 2：MQTT 连接失败

```
[ERROR] Failed to connect to MQTT: Name or service not known
```

**解决方案：**
```bash
# 1. 检查网络连接
ping 20.205.107.61

# 2. 检查防火墙
sudo ufw allow 1883

# 3. 使用本地 MQTT broker 测试
python3 lora_gateway.py --broker 127.0.0.1
```

### 问题 3：缺少加密库

```
[ERROR] pycryptodome not installed!
```

**解决方案：**
```bash
pip install pycryptodome
# 或
python3 -m pip install pycryptodome
```

### 问题 4：MIC 验证失败

```
[ERROR] Parse error: MIC verification failed - packet may be corrupted
```

**可能原因：**
- 数据在传输中被破坏
- 密钥不匹配（确保 `SHARED_KEY` 与发送端一致）
- 通信参数不对（波特率、停止位等）

**解决方案：**
```bash
# 1. 检查波特率
python3 lora_gateway.py --port /dev/ttyUSB0 --baud 115200

# 2. 查看原始数据
grep "RX_ERROR" lora_gateway.log
```

---

## 📈 部署建议

### 生产环境设置

#### 1. 后台运行（使用 systemd）

创建 service 文件：`/etc/systemd/system/lora-gateway.service`

```ini
[Unit]
Description=LoRa Gateway Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ProductProgram/Gateway
ExecStart=/usr/bin/python3 lora_gateway.py --port /dev/ttyUSB0 --broker 20.205.107.61
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl start lora-gateway
sudo systemctl enable lora-gateway      # 开机自启
sudo systemctl status lora-gateway      # 查看状态
sudo journalctl -u lora-gateway -f      # 查看日志
```

#### 2. 日志轮换（防止磁盘满）

安装 `logrotate`：

```bash
sudo nano /etc/logrotate.d/lora-gateway
```

配置内容：
```
/home/pi/ProductProgram/Gateway/lora_gateway.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 pi pi
}
```

#### 3. 监控和告警

```bash
# 检查进程是否运行
ps aux | grep lora_gateway

# 定期检查日志
crontab -e
# 添加: 0 * * * * grep "ERROR" /home/pi/ProductProgram/Gateway/lora_gateway.log | wc -l
```

#### 4. 性能优化

```bash
# 调整网络缓冲
sudo sysctl -w net.core.rmem_max=134217728
sudo sysctl -w net.core.wmem_max=134217728

# 监视 CPU 和内存
top
free -h
```

---

## 📚 相关文件参考

| 文件 | 用途 |
|------|------|
| `lora_gateway.py` | **树莓派主程序** ✅ 新增 |
| `lora_packet_simulator.py` | 生成测试数据包 |
| `LORA_QUICK_REFERENCE.py` | 多语言后端实现参考 |
| `LORA_PROTOCOL_BACKEND_GUIDE.md` | 协议详细文档 |
| `terminal.py` | 原始示例（35位数字） |

---

## ✅ 检查清单

开启 LoRa 网关前的检查列表：

- [ ] Python 3.x 已安装
- [ ] 依赖包已安装（`pip install pyserial paho-mqtt pycryptodome`）
- [ ] 串口设备已连接（`ls /dev/ttyUSB0` 或类似）
- [ ] 串口权限已配置（`newgrp dialout`）
- [ ] MQTT broker 地址正确（`20.205.107.61` 或本地）
- [ ] 网络连接正常（`ping` broker 地址）
- [ ] 密钥匹配（`SHARED_KEY = b'ThisIsA128BitKey'`）
- [ ] 日志目录可写（通常在程序目录）

---

## 🎓 学习资源

- **LoRa 协议详解**：见 `LORA_PROTOCOL_BACKEND_GUIDE.md`
- **Python 实现**：见 `LORA_QUICK_REFERENCE.py`
- **数据包生成**：运行 `python3 lora_packet_simulator.py`

---

## 📞 常见问题

**Q: 如何修改 MQTT topic？**
A: 编辑 `lora_gateway.py` 中的常量：
```python
MQTT_TOPIC_RECEIVER = "lora/gateway/receiver"
MQTT_TOPIC_SIMULATOR = "lora/gateway/simulator"
```

**Q: 如何修改密钥？**
A: 编辑 `lora_gateway.py` 中的：
```python
SHARED_KEY = b'ThisIsA128BitKey'  # 改为你的 16 字节密钥
```

**Q: 支持多个 LoRa 模块吗？**
A: 可以，运行多个实例，指定不同的 `--port`：
```bash
python3 lora_gateway.py --port /dev/ttyUSB0 &
python3 lora_gateway.py --port /dev/ttyUSB1 &
```

---

**版本**：1.0  
**更新日期**：2023-10-27  
**适配环境**：Raspberry Pi OS (Bullseye/Bookworm), Windows 10/11
