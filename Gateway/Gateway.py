import RPi.GPIO as GPIO
import time
import serial
import threading

# ===== GPIO 设置 =====
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

enablePin = 22    # EN：低电平工作，高电平休眠 :contentReference[oaicite:1]{index=1}
setPin = 16       # SET：按需使用；普通透明传输建议保持低
auxCheckPin = 18  # AUX：通讯状态指示 :contentReference[oaicite:2]{index=2}

# AUX 忙/闲电平：通常 0=忙，1=闲；如果你实测相反，改这里
AUX_IDLE = 1
AUX_BUSY = 0


def initGPIO():
    GPIO.setup(enablePin, GPIO.OUT)
    GPIO.setup(setPin, GPIO.OUT)
    # 内部上拉（有些模块AUX是开漏输出，弱上拉可能不够；必要时外接 4.7k~10k 上拉到3.3V）
    GPIO.setup(auxCheckPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # 启动即进入工作模式（更稳定）
    GPIO.output(enablePin, GPIO.LOW)
    GPIO.output(setPin, GPIO.LOW)

    time.sleep(0.1)
    # 手册：EN 拉低后要延迟 50ms 后才可以接收串口数据 :contentReference[oaicite:3]{index=3}
    time.sleep(0.06)


def wait_aux_idle(timeout=3.0):
    """等待 AUX 变为空闲（AUX_IDLE），超时返回 False"""
    start = time.time()
    while time.time() - start < timeout:
        if GPIO.input(auxCheckPin) == AUX_IDLE:
            return True
        time.sleep(0.001)
    return False


def aux_monitor(stop_event, interval=0.01):
    """后台实时打印 AUX 电平变化"""
    last = GPIO.input(auxCheckPin)
    print(f"[AUX] init={last} (idle={AUX_IDLE}, busy={AUX_BUSY})")
    while not stop_event.is_set():
        now = GPIO.input(auxCheckPin)
        if now != last:
            ts = time.strftime("%H:%M:%S")
            label = "IDLE" if now == AUX_IDLE else "BUSY"
            print(f"[AUX] {ts} {last} -> {now} ({label})")
            last = now
        time.sleep(interval)


def sendMessage(ser, data: str | bytes):
    try:
        # 发送前等空闲（更稳）
        if not wait_aux_idle(timeout=3.0):
            print("[WARN] AUX not idle before send (timeout)")

        payload = data.encode("utf-8") if isinstance(data, str) else data

        ser.write(payload)
        ser.flush()
        print(f"Sent: {payload!r}")

        # 发送后等空闲（用 AUX 判断发送处理完成）
        if not wait_aux_idle(timeout=3.0):
            print("[WARN] AUX not idle after send (timeout)")

    except Exception as e:
        print(f"Send Error: {e}")


if __name__ == "__main__":
    ser = None
    stop_event = threading.Event()
    t = None

    try:
        initGPIO()

        # 开启 AUX 实时监测线程
        t = threading.Thread(target=aux_monitor, args=(stop_event,), daemon=True)
        t.start()

        # 打开串口（如不通，改成 /dev/ttyAMA0 试试）
        ser = serial.Serial("/dev/ttyS0", 9600, timeout=1)
        print("Serial Port Opened:", ser.isOpen())

        while True:
            sendMessage(ser, "Hello LoRa\r\n")
            time.sleep(2)

    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        if ser and ser.isOpen():
            ser.close()
        GPIO.cleanup()
        print("Program Exited")
