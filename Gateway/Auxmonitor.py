import RPi.GPIO as GPIO
import time

# ===== GPIO 定义 =====
AUX_PIN = 27   # 根据你接线修改
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(AUX_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("=== AUX 状态监听开始 ===")
print("高电平 = 空闲 | 低电平 = 正在通信")
print("按 Ctrl+C 退出\n")

last_state = GPIO.input(AUX_PIN)

try:
    while True:
        current = GPIO.input(AUX_PIN)
        if current != last_state:
            state = "空闲 (HIGH)" if current == 1 else "忙碌 (LOW)"
            print(f"[{time.strftime('%H:%M:%S')}] AUX 状态变化 → {state}")
            last_state = current
        time.sleep(0.01)  # 10ms 轮询

except KeyboardInterrupt:
    print("\n退出监听")
finally:
    GPIO.cleanup()
