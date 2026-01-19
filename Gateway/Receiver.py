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
PACKET_LEN = 16
BIT_PULSE_S = 0.002

def init_gpio():
    GPIO.setup(MD0_PIN, GPIO.OUT)
    GPIO.setup(MD1_PIN, GPIO.OUT)
    GPIO.setup(AUX_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(ONE_PIN, GPIO.OUT)
    GPIO.setup(ZERO_PIN, GPIO.OUT)

    # 常开工作模式（更稳）
    GPIO.output(MD0_PIN, GPIO.LOW)
    GPIO.output(MD1_PIN, GPIO.HIGH)
    GPIO.output(ONE_PIN, GPIO.LOW)
    GPIO.output(ZERO_PIN, GPIO.LOW)

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

def parse_packet(packet: bytes) -> dict:
    if len(packet) != PACKET_LEN:
        raise ValueError(f"unexpected packet length: {len(packet)}")
    return {
        "device_id": int.from_bytes(packet[0:4], "big"),
        "temperature": int.from_bytes(packet[4:6], "big"),
        "humidity": int.from_bytes(packet[6:8], "big"),
        "distance": int.from_bytes(packet[8:10], "big"),
        "mq4": int.from_bytes(packet[10:12], "big"),
        "mq136": int.from_bytes(packet[12:14], "big"),
        "reserved": packet[14:16],
    }

def receiver_loop(ser: serial.Serial, stop_event: threading.Event):
    print("=== Receiver started (waiting data) ===")
    buffer = bytearray()
    while not stop_event.is_set():
        try:
            if GPIO.input(AUX_PIN) == AUX_BUSY:
                if not wait_aux_idle(stop_event=stop_event):
                    continue
            chunk = ser.read(PACKET_LEN)
            if not chunk:
                continue
            buffer.extend(chunk)
            while len(buffer) >= PACKET_LEN:
                packet = bytes(buffer[:PACKET_LEN])
                del buffer[:PACKET_LEN]

                ts = time.strftime("%H:%M:%S")
                parsed = parse_packet(packet)
                print(f"[{ts}] RX(hex) : {format_hex(packet)}")
                print(
                    f"[{ts}] id=0x{parsed['device_id']:08X} "
                    f"temp={parsed['temperature']} "
                    f"hum={parsed['humidity']} "
                    f"dist={parsed['distance']} "
                    f"mq4={parsed['mq4']} "
                    f"mq136={parsed['mq136']}"
                )
                emit_packet_bits(packet)

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
