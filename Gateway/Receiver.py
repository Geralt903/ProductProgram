import RPi.GPIO as GPIO
import time
import serial
import threading

# ===== GPIO =====
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

EN_PIN = 22
SET_PIN = 16
AUX_PIN = 18

AUX_IDLE = 1
AUX_BUSY = 0

def init_gpio():
    GPIO.setup(EN_PIN, GPIO.OUT)
    GPIO.setup(SET_PIN, GPIO.OUT)
    GPIO.setup(AUX_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # 常开工作模式（更稳）
    GPIO.output(EN_PIN, GPIO.LOW)
    GPIO.output(SET_PIN, GPIO.LOW)

    time.sleep(0.1)
    # 手册：EN 拉低后 >=50ms 才能接收串口数据 :contentReference[oaicite:1]{index=1}
    time.sleep(0.06)

def aux_monitor(stop_event, interval=0.01):
    last = GPIO.input(AUX_PIN)
    print(f"[AUX] init={last} (idle={AUX_IDLE}, busy={AUX_BUSY})")
    while not stop_event.is_set():
        now = GPIO.input(AUX_PIN)
        if now != last:
            ts = time.strftime("%H:%M:%S")
            label = "IDLE" if now == AUX_IDLE else "BUSY"
            print(f"[AUX] {ts} {last} -> {now} ({label})")
            last = now
        time.sleep(interval)

def format_hex(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)

def receiver_loop(ser: serial.Serial, stop_event: threading.Event):
    print("=== Receiver started (waiting data) ===")
    while not stop_event.is_set():
        try:
            # 读到就打印（按行更直观；如果对方不发 \n，可改成 ser.read）
            line = ser.readline()
            if not line:
                continue

            ts = time.strftime("%H:%M:%S")
            # 尝试按 utf-8 解码，不行就替换乱码
            text = line.decode("utf-8", errors="replace").rstrip("\r\n")

            print(f"[{ts}] RX(text): {text}")
            print(f"[{ts}] RX(hex) : {format_hex(line)}")

        except Exception as e:
            print("Receiver error:", e)
            time.sleep(0.1)

if __name__ == "__main__":
    ser = None
    stop_event = threading.Event()
    t_aux = None
    try:
        init_gpio()

        # 串口：按你实际情况改 /dev/ttyS0 或 /dev/ttyAMA0
        ser = serial.Serial("/dev/ttyS0", 9600, timeout=1)
        print("Serial opened:", ser.isOpen())

        # AUX 监测线程
        t_aux = threading.Thread(target=aux_monitor, args=(stop_event,), daemon=True)
        t_aux.start()

        # 接收主循环
        receiver_loop(ser, stop_event)

    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        if ser and ser.isOpen():
            ser.close()
        GPIO.cleanup()
        print("Program Exited")
