import socket
import struct
import win32api
import win32con

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

sensitivity = 0.5  # tune gyro sensitivity to taste

print("Listening for IMU data...")
while True:
    data, addr = sock.recvfrom(1024)
    if len(data) != 24:  # 6 floats * 4 bytes each
        continue

    # Unpack accel and gyro
    ax, ay, az, gx, gy, gz = struct.unpack('ffffff', data)

    # Optional: print for debugging
    print(f"Accel: ({ax:.2f}, {ay:.2f}, {az:.2f}) | Gyro: ({gx:.2f}, {gy:.2f}, {gz:.2f})")

    # Convert gyro to mouse movement
    dx = int(gx * sensitivity)
    dy = int(-gy * sensitivity)  # invert Y if needed

    if dx or dy:
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy)

    # Acceleration variables (ax, ay, az) are available here for future features
