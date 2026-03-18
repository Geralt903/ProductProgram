import argparse
import sys
import time

import serial


def main():
    parser = argparse.ArgumentParser(description="Simple serial listener for Raspberry Pi")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port path")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate")
    parser.add_argument("--timeout", type=float, default=1.0, help="Read timeout in seconds")
    args = parser.parse_args()

    ser = serial.Serial(args.port, args.baud, timeout=args.timeout)
    print(f"Listening on {args.port} @ {args.baud} baud. Ctrl+C to stop.")

    try:
        while True:
            data = ser.readline()
            if not data:
                time.sleep(0.01)
                continue
            sys.stdout.buffer.write(data)
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()


if __name__ == "__main__":
    main()
