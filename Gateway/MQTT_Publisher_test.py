import paho.mqtt.client as mqtt
import time

# !!! 把这里改成你云服务器的公网 IP !!!
BROKER_ADDRESS = "20.205.107.61"
TOPIC = "test/stm32"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ [发送端] 已连接到服务器")
    else:
        print(f"❌ [发送端] 连接失败，错误码: {rc}")

client = mqtt.Client()
client.on_connect = on_connect

try:
    print(f"⏳ [发送端] 正在连接...")
    client.connect(BROKER_ADDRESS, 1883, 60)
    
    # 开启网络循环（后台线程处理网络包）
    client.loop_start()
    time.sleep(1) # 给一点时间建立连接

    # 发送一条测试消息
    msg = "Hello! 这是来自发送端的测试消息!"
    info = client.publish(TOPIC, msg)
    info.wait_for_publish() # 确保发送出去了
    print(f"🚀 [发送端] 消息已发送: '{msg}'")

    client.loop_stop()
    client.disconnect()

except Exception as e:
    print(f"❌ 发生错误: {e}")