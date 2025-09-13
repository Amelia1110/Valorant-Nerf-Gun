# ESP8266 Gyroscope Mouse Controller

This directory contains two versions of ESP8266 code for the gyroscope mouse controller:

## Files

### 1. `esp8266_example.ino` - Simulated Gyroscope (Demo Version)
- **Use case**: Testing and demonstration without real sensors
- **Hardware**: ESP8266 only (no additional sensors needed)
- **Limitations**: Simulates 3-axis gyroscope data using only A0 pin
- **Good for**: Prototyping, testing Python backend, learning the system

### 2. `esp8266_mpu6050.ino` - Real MPU6050 Sensor (Production Version)
- **Use case**: Real gyroscope control with actual sensor
- **Hardware**: ESP8266 + MPU6050 gyroscope/accelerometer
- **Connections**: I2C communication (SDA=D2, SCL=D1)
- **Good for**: Actual mouse control with real sensor data

## Hardware Connections

### For MPU6050 Version:
```
ESP8266    MPU6050
------     -------
3.3V   ->  VCC
GND    ->  GND
D2     ->  SDA
D1     ->  SCL
```

## Configuration

### WiFi Settings
Update these in both files:
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* server_ip = "192.168.1.100";  // Your PC's IP address
```

### Python Server IP
1. Find your PC's IP address:
   - Windows: `ipconfig`
   - Mac/Linux: `ifconfig`
2. Update `server_ip` in the Arduino code
3. Make sure both devices are on the same network

## Key Fixes Applied

### 1. ADC Pin Limitation ✅
- **Problem**: ESP8266 only has 1 ADC pin (A0), not A1, A2
- **Solution**: 
  - Demo version: Simulates 3-axis data from single A0 input
  - MPU6050 version: Uses I2C for real 3-axis sensor

### 2. WiFi Reconnection ✅
- **Problem**: Code only reconnected to server, not WiFi
- **Solution**: Added periodic WiFi status checking and reconnection
- **Features**:
  - Checks WiFi every 30 seconds
  - Automatically reconnects if disconnected
  - Graceful error handling

### 3. JSON Message Boundaries ✅
- **Problem**: TCP stream could split JSON messages
- **Solution**: 
  - Always use `client.println()` (adds `\n`)
  - Python backend splits on newlines
  - Proper message buffering

### 4. Connection Management ✅
- **Problem**: Poor error handling and reconnection logic
- **Solution**:
  - Separate WiFi and server connection functions
  - Periodic connection checking
  - Non-blocking reconnection attempts
  - Clear status messages

## Usage Instructions

### 1. Upload Code
1. Open Arduino IDE
2. Install ESP8266 board package
3. Select your ESP8266 board
4. Upload the appropriate `.ino` file

### 2. Monitor Serial Output
```
ESP8266 Gyroscope Mouse Controller
==================================
Connecting to WiFi...
WiFi connected!
IP address: 192.168.1.105
MPU6050 initialized successfully!
Connecting to Python server...
Connected to Python server!
```

### 3. Run Python Backend
```bash
cd backend
pip install -r requirements.txt
python mouse_fol_gy.py
```

## Troubleshooting

### Common Issues

1. **"WiFi connection failed"**
   - Check SSID and password
   - Ensure 2.4GHz network (ESP8266 doesn't support 5GHz)
   - Check signal strength

2. **"Server connection failed"**
   - Verify PC IP address
   - Check if Python server is running
   - Ensure both devices on same network
   - Check firewall settings

3. **"MPU6050 initialization failed"**
   - Check wiring (SDA=D2, SCL=D1)
   - Verify 3.3V power supply
   - Check I2C pull-up resistors (4.7kΩ)

4. **Mouse not moving**
   - Check Python server output
   - Verify JSON data format
   - Check calibration status
   - Adjust sensitivity settings

### Debug Tips

1. **Monitor Serial Output**: Use Arduino IDE Serial Monitor (115200 baud)
2. **Check Python Logs**: Look for connection and calibration messages
3. **Test JSON Format**: Verify data format matches expected structure
4. **Network Testing**: Ping between devices to test connectivity

## Performance Notes

- **Update Rate**: 100Hz (10ms delay)
- **Data Format**: JSON with x, y, z gyroscope values
- **Connection**: TCP on port 12345
- **Power**: 3.3V operation (ESP8266 + MPU6050)

## Next Steps

1. **Choose Version**: Start with demo version for testing
2. **Hardware Setup**: Add MPU6050 for real sensor data
3. **Calibration**: Hold device steady during initial calibration
4. **Tuning**: Adjust sensitivity and smoothing in Python code
5. **Integration**: Connect to your Valorant Nerf Gun project!
