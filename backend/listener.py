import socket
import struct
import win32api
import win32con
from pynput.keyboard import Controller as KeyboardController
from pynput.mouse import Controller as MouseController, Button

keyboard = KeyboardController()
mouse = MouseController()

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

sensitivity = 0.5  # tune gyro sensitivity to taste

print("Listening for IMU data...")
while True:
    data, addr = sock.recvfrom(1024)
    if len(data) != 25:  # 6 floats * 4 bytes each
        continue

    # Gyro
    # Unpack accel and gyro
    ax, ay, az, gx, gy, gz = struct.unpack('ffffff', data[:24])
    
    # Optional: print for debugging
    print(f"Accel: ({ax:.2f}, {ay:.2f}, {az:.2f}) | Gyro: ({gx:.2f}, {gy:.2f}, {gz:.2f})")

    # cnvert gyro to mouse movement
    dx = int(-gz * sensitivity)
    dy = int(gx * sensitivity)  

    if dx or dy:
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy)


    # Buttons
    # last byte = buttons bitmask
    buttons = data[24]

    # bit 0 = 'R' (tap), bit 1 = left mouse (hold)
    # check changes
    for bit in (0, 1):
        mask = 1 << bit
        now = bool(buttons & mask)
        before = bool(last_buttons & mask)

        if bit == 0:  # 'R' key – fire on rising edge only
            if now and not before:
                keyboard.press('r')
                print("R Pressed")
                keyboard.release('r')

        if bit == 1:  # left mouse – hold style
            if now and not before:
                mouse.press(Button.left)
                print("Left Mouse Pressed")
            elif not now and before:
                mouse.release(Button.left)

    last_buttons = buttons
