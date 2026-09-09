 #!/usr/bin/env python3
"""
LeafLabs Maple Handbrake → Existing Xbox Controller Axis bridge
"""

import os
import sys
import time
import struct
import evdev
from evdev import InputDevice, ecodes as e
import subprocess

def start_xboxdrv():
    """Start xboxdrv daemon as a subprocess"""
    try:
        # Start xboxdrv in daemon mode
        process = subprocess.Popen(
            ['xboxdrv', '--daemon', '--silent', '--mimic-xpad', '--type', 'xbox360'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        print("Starting xboxdrv...")
        # Give it time to initialize
        time.sleep(2)

        # Check if it's still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"ERROR: xboxdrv failed to start")
            print(f"stdout: {stdout.decode()}")
            print(f"stderr: {stderr.decode()}")
            return None

        print("xboxdrv started successfully")
        return process

    except FileNotFoundError:
        print("ERROR: xboxdrv not found. Install with: sudo apt install xboxdrv")
        return None
    except Exception as e:
        print(f"ERROR starting xboxdrv: {e}")
        return None

def find_xbox_controller():
    """Find the existing Xbox 360 controller (event17)"""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        if "Microsoft X-Box 360 pad" in device.name:
            print(f"Found Xbox controller: {device.path} ({device.name})")
            return device.path

    print("ERROR: No Xbox 360 controller found!")
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

def cleanup_xboxdrv():
    """Kill any existing xboxdrv processes"""
    try:
        subprocess.run(['pkill', '-9', 'xboxdrv'],  
            stdout=subprocess.DEVNULL,  
            stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    except:
        pass

def main():
    if os.geteuid() != 0:
        print("ERROR: Run with sudo for evdev access")
        sys.exit(1)

    print("Cleaning up old xboxdrv instances...")
    cleanup_xboxdrv()

    xboxdrv_process = start_xboxdrv()
    if not xboxdrv_process:
        sys.exit(1)

    # Find devices
    xbox_path = find_xbox_controller()
    hidraw_path = find_hidraw_device()

    if not hidraw_path:
        print("ERROR: LeafLabs Maple not found!")
        sys.exit(1)

    print(f"Handbrake: {hidraw_path}")
    print(f"Xbox: {xbox_path}")
    print("Bridging handbrake data into Xbox LT trigger...")
    print("Press Ctrl+C to stop\n")

    # Open Xbox device for writing
    xbox_fd = os.open(xbox_path, os.O_RDWR | os.O_NONBLOCK)

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

                # FIX: Convert time.time() float → integers (sec, usec)
                now = time.time()
                sec = int(now)
                usec = int((now - sec) * 1000000)

                # ABS_RY event (Right Stick)
                # normal_evdev_trigger = axis_value
                # evdev_trigger = int(normal_evdev_trigger) - 32767
                # abs_event = struct.pack('llHHi', sec, usec, e.EV_ABS, e.ABS_RY, evdev_trigger)

                # ABS_Z event (Left Trigger)                
                # Normalize to Xbox trigger range (0-32767 for evdev ABS)
                normal_evdev_trigger = axis_value * 255 // 65472.0
                evdev_trigger = int(normal_evdev_trigger)
                abs_event = struct.pack('llHHI', sec, usec, e.EV_ABS, e.ABS_Z, evdev_trigger)
                # SYN event
                syn_event = struct.pack('llHHI', sec, usec, e.EV_SYN, 0, 0)

                # Write both events
                os.write(xbox_fd, abs_event + syn_event)
                print(f"Handbrake: {axis_value} → LT: {evdev_trigger:5d} LT before int(): {normal_evdev_trigger}", end='\r')

                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as err:
        print(f"\nERROR: {err}")
    finally:
        os.close(xbox_fd)

cleanup_xboxdrv()
if __name__ == "__main__":
    main()
