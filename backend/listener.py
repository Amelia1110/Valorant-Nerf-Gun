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
last_joystickFwd = 0
last_joystickSide = 0

print("Listening for IMU data...")
while True:
    data, addr = sock.recvfrom(1024)
    if len(data) != 33:
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

    # debug current raw mask (throttled by simple change detection)
    if buttons != last_buttons:
        print(f"Buttons mask: 0x{buttons:02X}")

    # bit 0 = 'R' (tap), bit 1 = left mouse (hold), bit 2 = space (tap)
    # check changes for bits 0,1,2
    for bit in (0, 1, 2, 3):
        mask = 1 << bit
        now = bool(buttons & mask)
        before = bool(last_buttons & mask)

        if bit == 0:  # 'R' key – fire on rising edge only
            if now and not before:
                keyboard.press('r')
                print("R Pressed")
                keyboard.release('r')

        if bit == 1:  # left mouse hold
            if now and not before:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                print("Left Mouse DOWN")
            elif not now and before:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                print("Left Mouse UP")

        if bit == 2:  # jump tap
            if now and not before:
                keyboard.press(Key.space)
                keyboard.release(Key.space)
                
        if bit == 3: # mouse scroll down
            if now and not before:
                mouse.scroll(0, -1)
                print("Scroll Down")

        if bit == 4:  # right mouse hold
            if now and not before:
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
                print("Left Mouse Click")

    last_buttons = buttons


    # Joystick
    joystickFwd, joystickSide = struct.unpack('ff', data[25:33])

    walk_thresh = 0.2     # 0.2–0.5 = walk
    run_thresh = 0.5      # 0.5–0.8 = run
    crouch_thresh = 0.8   # 0.8+ = crouch / max speed (backwards example)

    # release previously held keys first
    if abs(last_joystickFwd) > 0.1:  # if there was movement before
        keyboard.release('w')
        keyboard.release('s')
        keyboard.release(Key.shift_l)
        keyboard.release('c')  # if crouch key

    if abs(last_joystickSide) > 0.1:  # if there was movement before
        keyboard.release('d')
        keyboard.release('a')
        keyboard.release(Key.shift_l)
        keyboard.release('c')  # if crouch key

    # forward (positive joystick)
    if joystickFwd > 0.1:
        if joystickFwd <= walk_thresh:
            keyboard.press('w')
            keyboard.press(Key.shift_l)  # walk
        elif joystickFwd <= run_thresh:
            keyboard.press('w')       # run
        else:  
            keyboard.press('w')       # maximum run / sprint (could map to crouch if backward)

    # backward (negative joystick)
    elif joystickFwd < -0.1:
        abs_j = abs(joystickFwd)
        if abs_j <= walk_thresh:
            keyboard.press('s')
            keyboard.press(Key.shift_l)  # walk backwards
        elif abs_j <= run_thresh:
            keyboard.press('s')       # run backward
        else:
            keyboard.press('s')       # crouch/backpedal max

    last_joystickFwd = joystickFwd

    # right (positive joystick)
    if joystickSide > 0.1:
        if joystickSide <= walk_thresh:
            keyboard.press('d')
            keyboard.press(Key.shift_l)  # walk right
        elif joystickSide <= run_thresh:
            keyboard.press('d')       # run right
        else:  
            keyboard.press('d')       # maximum run / sprint

    # left (negative joystick)
    elif joystickSide < -0.1:
        abs_j = abs(joystickSide)
        if abs_j <= walk_thresh:
            keyboard.press('a')
            keyboard.press(Key.shift_l)  # walk left
        elif abs_j <= run_thresh:
            keyboard.press('a')       # run left
        else:
            keyboard.press('a')       # crouch/backpedal max

    last_joystickSide = joystickSide
