import RPi.GPIO as GPIO
import time
import serial
import threading

# ===== GPIO =====
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

MD0_PIN = 22
MD1_PIN = 16
AUX_PIN = 18
ONE_PIN = 23
ZERO_PIN = 24

AUX_IDLE = 1
AUX_BUSY = 0
PACKET_DIGITS = 35
TEMP_SCALE = 100.0
HUM_SCALE = 100.0
DIST_SCALE = 100.0
BIT_PULSE_S = 0.002

def set_md_pin(pin: int, high: bool) -> None:
    if high:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
    else:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

def init_gpio():
    GPIO.setup(AUX_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(ONE_PIN, GPIO.OUT)
    GPIO.setup(ZERO_PIN, GPIO.OUT)

    # 常开工作模式（更稳）
    # A39C: MD0/MD1 内部上拉，高电平用输入悬空
    set_md_pin(MD0_PIN, True)
    set_md_pin(MD1_PIN, False)
    GPIO.output(ONE_PIN, GPIO.LOW)
    GPIO.output(ZERO_PIN, GPIO.LOW)

    time.sleep(0.1)
    # 手册：模块上电初始化 >=50ms 才能接收串口数据
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

def wait_aux_idle(stop_event: threading.Event | None = None, interval=0.01) -> bool:
    if GPIO.input(AUX_PIN) == AUX_IDLE:
        return True
    print("[AUX] BUSY -> waiting for IDLE")
    last = GPIO.input(AUX_PIN)
    while GPIO.input(AUX_PIN) != AUX_IDLE:
        if stop_event is not None and stop_event.is_set():
            return False
        now = GPIO.input(AUX_PIN)
        if now != last:
            ts = time.strftime("%H:%M:%S")
            label = "IDLE" if now == AUX_IDLE else "BUSY"
            print(f"[AUX] {ts} {last} -> {now} ({label})")
            last = now
        time.sleep(interval)
    ts = time.strftime("%H:%M:%S")
    print(f"[AUX] {ts} idle")
    return True

def format_hex(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)

def output_bit(bit: int, pulse_s: float = BIT_PULSE_S) -> None:
    if bit:
        GPIO.output(ONE_PIN, GPIO.HIGH)
        GPIO.output(ZERO_PIN, GPIO.LOW)
    else:
        GPIO.output(ONE_PIN, GPIO.LOW)
        GPIO.output(ZERO_PIN, GPIO.HIGH)
    time.sleep(pulse_s)
    GPIO.output(ONE_PIN, GPIO.LOW)
    GPIO.output(ZERO_PIN, GPIO.LOW)

def emit_packet_bits(packet: bytes) -> None:
    for byte in packet:
        for bit_index in range(7, -1, -1):
            output_bit((byte >> bit_index) & 1)

def parse_digit_packet(digits: str) -> dict:
    if len(digits) != PACKET_DIGITS or not digits.isdigit():
        raise ValueError(f"unexpected packet digits: {digits!r}")
    temperature_raw = int(digits[10:15])
    humidity_raw = int(digits[15:20])
    distance_raw = int(digits[20:25])
    mq4_raw = int(digits[25:30])
    mq136_raw = int(digits[30:35])
    return {
        "device_id": int(digits[0:10]),
        "temperature_raw": temperature_raw,
        "humidity_raw": humidity_raw,
        "distance_raw": distance_raw,
        "mq4": mq4_raw,
        "mq136": mq136_raw,
        "temperature": temperature_raw / TEMP_SCALE,
        "humidity": humidity_raw / HUM_SCALE,
        "distance": distance_raw / DIST_SCALE,
    }

def receiver_loop(ser: serial.Serial, stop_event: threading.Event):
    print("=== Receiver started (waiting data) ===")
    digit_buffer = []
    while not stop_event.is_set():
        try:
            if GPIO.input(AUX_PIN) == AUX_BUSY:
                if not wait_aux_idle(stop_event=stop_event):
                    continue
            chunk = ser.read(128)
            if not chunk:
                continue
            for byte in chunk:
                if 48 <= byte <= 57:
                    digit_buffer.append(chr(byte))
                else:
                    if digit_buffer:
                        digit_buffer.clear()
            while len(digit_buffer) >= PACKET_DIGITS:
                digits = "".join(digit_buffer[:PACKET_DIGITS])
                del digit_buffer[:PACKET_DIGITS]

                ts = time.strftime("%H:%M:%S")
                parsed = parse_digit_packet(digits)
                print(f"[{ts}] RX(digits): {digits}")
                print(
                    f"[{ts}] id={parsed['device_id']:010d} "
                    f"temp={parsed['temperature']:.2f} "
                    f"hum={parsed['humidity']:.2f} "
                    f"dist={parsed['distance']:.2f} "
                    f"mq4={parsed['mq4']} "
                    f"mq136={parsed['mq136']}"
                )
                emit_packet_bits(digits.encode("ascii"))

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
