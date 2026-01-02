from RPi.GPIO import GPIO
import time
import serial

# GPIO 设置
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

enablePin = 22   # 22低电平使能 (工作模式)
setPin = 16      # 16 高电平可能用于进入配置模式(根据你的注释)，平时保持低电平
auxCheckPin = 27 # 27 辅助检测 (AUX)

def initGPIO():
    GPIO.setup(enablePin, GPIO.OUT)
    GPIO.setup(setPin, GPIO.OUT)
    GPIO.setup(auxCheckPin, GPIO.IN)
    
    # 初始状态：EN高(休眠/禁用)，SET低(非配置状态)
    GPIO.output(enablePin, GPIO.HIGH) 
    GPIO.output(setPin, GPIO.LOW) 
    time.sleep(0.1)

def sendMessage(ser, data):
    """
    发送数据函数
    :param ser: 已打开的串口对象
    :param data: 要发送的字符串或字节数据
    """
    try:
        # 1. 拉低 EN 引脚唤醒模块
        # 手册说明：EN脚置低恢复正常工作
        GPIO.output(enablePin, GPIO.LOW)
        
        # 2. 必须的延时
        # 手册说明：EN拉低后要延迟 50ms 后才可以接收串口数据
        time.sleep(0.06) 

        # 3. 处理数据格式 (转为bytes)
        if isinstance(data, str):
            data_to_send = data.encode('utf-8')
        else:
            data_to_send = data
            
        # 4. 串口发送
        ser.write(data_to_send)
        print(f"Sent: {data_to_send}")

        # 5. 等待发送完成 (可选)
        # 可以通过检测 AUX 引脚状态来判断模块是否处理完毕
        # 简单处理可以加一点延时，或者检测 AUX
        # while GPIO.input(auxCheckPin) == 0: # 假设低电平代表忙
        #     time.sleep(0.001)
        time.sleep(0.1) 

    except Exception as e:
        print(f"Send Error: {e}")
    finally:
        # 6. 发送结束后，如果需要省电，可以拉高 EN 进入休眠
        # 如果需要持续接收，则不要拉高
        # GPIO.output(enablePin, GPIO.HIGH) 
        pass

# --- 主程序示例 ---
if __name__ == '__main__':
    try:
        # 初始化GPIO
        initGPIO()
        
        # 初始化串口
        # 注意：树莓派上的串口通常是 '/dev/ttyS0' 或 '/dev/ttyAMA0'
        # 波特率默认为 9600 (手册默认值)
        ser = serial.Serial('/dev/ttyS0', 9600, timeout=1)
        
        if ser.isOpen():
            print("Serial Port Opened")
            
        # 发送测试消息
        while True:
            sendMessage(ser, "Hello LoRa")
            time.sleep(2) # 每隔2秒发一次

    except KeyboardInterrupt:
        if ser:
            ser.close()
        GPIO.cleanup()
        print("Program Exited")