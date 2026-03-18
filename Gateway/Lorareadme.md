# LoRa 终端脚本说明（terminal.py）

本文件仅保留当前项目的最小功能说明：

## 功能
- 从串口读取数据。
- 将读取到的数据发布到 MQTT 主题。

## 对应脚本
- `ProductProgram/Gateway/terminal.py`

## 关键配置（与脚本一致）
- `BROKER_ADDRESS = "20.205.107.61"`
- `TOPIC = "test/stm32"`
- `SERIAL_PORT = "/dev/ttyS0"`
- `BAUD_RATE = 9600`

## 运行
```bash
python ProductProgram/Gateway/terminal.py
```

## 说明
- 串口无数据时会短暂休眠并继续读取。
- 收到的数据会原样发布到 MQTT 主题。