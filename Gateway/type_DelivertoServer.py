import Gateway
import paho.mqtt.client as mqtt
import json
import time

def on_connect(client, userdata, flags, rc):
    print("已连接到服务器，代码:", rc)
    # 订阅控制频道，准备接收云端指令
    client.subscribe("gateway/control")

def on_message(client, userdata, msg):
    print(f"收到指令: {msg.payload.decode()}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# 连接到 MQTT 服务器 (Broker)
client.connect("mqtt.example.com", 1883, 60)

client.loop_start() # 开启后台线程处理网络接收

while True:
    # 模拟采集到的传感器数据
    payload = json.dumps({"temp": 25.5, "humidity": 60})
    client.publish("gateway/data", payload) # 发布数据
    print("数据已上报")
    time.sleep(5)
