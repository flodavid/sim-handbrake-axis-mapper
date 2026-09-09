 #!/usr/bin/env python3
"""
LeafLabs Maple Handbrake axis mapping
"""

import os
import sys
import time
import struct
import evdev
from evdev import InputDevice, ecodes as e

def find_handbrake_controller():
    """Find the existing LeafsLabs Maple handbrake controller"""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        if "LeafLabs Maple" in device.name:
            print(f"Found handbrake controller: {device.path} ({device.name})")
            return device.path

    print("ERROR: No handbrake controller found!")
    sys.exit(1)

def find_hidraw_device():
    """Find the LeafLabs Maple handbrake and wait if not present."""
    print("Waiting for LeafLabs Maple handbrake...")
    while True:
        for i in range(20):
            hidraw_path = f"/dev/hidraw{i}"
            uevent_path = f"/sys/class/hidraw/hidraw{i}/device/uevent"

            if not os.path.exists(hidraw_path):
                continue

            try:
                with open(uevent_path, 'r') as f:
                    content = f.read()
                    if '1EAF' in content and '0024' in content:
                        print(f"Found handbrake at {hidraw_path}\n")
                        return hidraw_path
                    if 'HID_NAME=LeafLabs Maple' in content:
                        print(f"Found 'LeafLabs Maple' handbrake at {hidraw_path}, with device ID is unknown though")
                        return hidraw_path
            except:
                continue

        print("Handbrake not found, waiting 2 seconds...")
        time.sleep(2) # Wait before next scan [web:11][cite:1]

def main():
    if os.geteuid() != 0:
        print("ERROR: Run with sudo for evdev access")
        sys.exit(1)

    # Find devices
    handbrake_path = find_handbrake_controller()
    hidraw_path = find_hidraw_device()

    if not hidraw_path:
        print("ERROR: LeafLabs Maple not found!")
        sys.exit(1)

    print(f"Handbrake: {hidraw_path}")
    print("Press Ctrl+C to stop\n")

    # Open handbrake device for writing
    handbrake_fd = os.open(handbrake_path, os.O_RDWR | os.O_NONBLOCK)

    try:
        with open(hidraw_path, 'rb') as hidraw:
            while True:
                # Read HID report (13 bytes)
                data = hidraw.read(13)

                if len(data) < 13:
                    time.sleep(0.01)
                    continue

                # Extract axis from bytes 11-12 (0-65535)
                low_byte = data[11]
                high_byte = data[12]
                axis_value = low_byte | (high_byte << 8)

                now = time.time()
                sec = int(now)
                usec = int((now - sec) * 1000000)

                # ABS_RX event
                # Normalize from LeafLabs Maple handbrake trigger range (0-65472 for evdev ABS) to 0-1023 value
                normal_evdev_trigger = axis_value / 64
                evdev_trigger = int(normal_evdev_trigger)
                abs_event = struct.pack('llHHI', sec, usec, e.EV_ABS, e.ABS_RX, evdev_trigger)
                # SYN event
                syn_event = struct.pack('llHHI', sec, usec, e.EV_SYN, 0, 0)

                # Write both events
                os.write(handbrake_fd, abs_event + syn_event)
                print(f"Handbrake: {axis_value:5d} → Axis: {evdev_trigger:4d}", end='\r')

                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as err:
        print(f"\nERROR: {err}")
    finally:
        os.close(handbrake_fd)

if __name__ == "__main__":
    main()
