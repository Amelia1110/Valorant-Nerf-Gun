import socket
import struct
import win32api
import win32con
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button

keyboard = KeyboardController()
mouse = MouseController()

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

sensitivity = 0.8  # tune gyro sensitivity to taste
last_buttons = 0
last_joystick = 0

print("Listening for IMU data...")
while True:
    data, addr = sock.recvfrom(1024)
    if len(data) != 29:
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
sss

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

        if bit == 2:  # jump tap
            if now and not before:
                keyboard.press('space')
                keyboard.release('space')

    last_buttons = buttons


    # Joystick
    joystick, = struct.unpack('f', data[25:29])

    walk_thresh = 0.2     # 0.2–0.5 = walk
    run_thresh = 0.5      # 0.5–0.8 = run
    crouch_thresh = 0.8   # 0.8+ = crouch / max speed (backwards example)

    # release previously held keys first
    if abs(last_joystick) > 0.1:  # if there was movement before
        keyboard.release('w')
        keyboard.release('s')
        keyboard.release(Key.shift_l)
        keyboard.release('c')  # if crouch key

    # forward (positive joystick)
    if joystick > 0.1:
        if joystick <= walk_thresh:
            keyboard.press('w')
            keyboard.press(Key.shift_l)  # walk
        elif joystick <= run_thresh:
            keyboard.press('w')       # run
        else:  
            keyboard.press('w')       # maximum run / sprint (could map to crouch if backward)

    # backward (negative joystick)
    elif joystick < -0.1:
        abs_j = abs(joystick)
        if abs_j <= walk_thresh:
            keyboard.press('s')
            keyboard.press(Key.shift_l)  # walk backwards
        elif abs_j <= run_thresh:
            keyboard.press('s')       # run backward
        else:
            keyboard.press('s')       # crouch/backpedal max

    last_joystick = joystick
