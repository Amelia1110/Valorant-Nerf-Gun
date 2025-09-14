import socket
import struct
import win32api
import win32con
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import time

keyboard = KeyboardController()
mouse = MouseController()

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

sensitivity = 0.8  # tune gyro sensitivity to taste
angle_threshold = 80.0

last_buttons = 0
last_joystick = 0

print("Listening for IMU data...")

# Integration status
last_time = time.time()
angle_z = 0.0
origin_angle = 0.0

while True:
    data, addr = sock.recvfrom(1024)
    now = time.time()
    dt = now - last_time
    if dt <= 0:
        dt = 0.01
    last_time = now

    if len(data) != 29:
        continue

    # Gyro
    # Unpack accel and gyro
    ax, ay, az, gx, gy, gz = struct.unpack('ffffff', data[:24])

    # gx/gy/gz are degrees per second, integrate gz to get degrees rotated around z
    delta_deg_z = gz * dt
    angle_z += delta_deg_z
    
    # Optional: print for debugging
    print(f"Accel: ({ax:.2f}, {ay:.2f}, {az:.2f}) | Gyro: ({gx:.2f}, {gy:.2f}, {gz:.2f})")
    print(f"gz: {gz:.2f} degree per second, dt: {dt:.4f}s, delta deg z: {delta_deg_z:.3f} degrees, angle z: {angle_z:.3f} degrees")

    # alerts if it's rotated over 80 degrees
    if abs(angle_z - origin_angle) >= angle_threshold:
        # direction: +1 if rotated right (gz>0), -1 if left
        direction = 1 if gz > 0 else -1

        # speed: proportional to how fast you’re rotating
        # scale factor: adjust sensitivity to taste
        speed = int(direction * abs(gz) * sensitivity * 0.5)

        # apply continuous mouse move
        if speed != 0:
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, speed, 0)

        # Debug
        print(f"Rotating: {angle_z:.1f}°, gz={gz:.1f}, speed={speed}")

    else:
        # within threshold → stop moving
        pass

    # cnvert gyro to mouse movement
    dx = int(-gz * sensitivity * dt)
    dy = int(gx * sensitivity * dt)  

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
