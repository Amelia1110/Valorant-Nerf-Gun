import socket
import json
import time
import threading
import win32api  # Direct Windows API access for mouse control
import win32con  # Windows constants for system metrics
import math
from collections import deque
import numpy as np

class GyroMouseController:
    def __init__(self, host='0.0.0.0', port=12345, sensitivity=1.0, smoothing_factor=0.3):
        """
        Initialize the gyroscope mouse controller
        
        This function sets up all the necessary variables and configurations for the
        gyroscope mouse control system. It initializes data storage, calibration settings,
        smoothing buffers, and prepares the system for WiFi communication.
        
        Args:
            host: IP address to bind the server to (default: '0.0.0.0' for all interfaces)
            port: Port number for WiFi communication (default: 12345)
            sensitivity: Mouse movement sensitivity multiplier (default: 1.0)
            smoothing_factor: Factor for smoothing gyroscope data (0-1, lower = more smoothing)
        """
        # Store configuration parameters
        self.host = host  # IP address for the server to listen on
        self.port = port  # Port number for WiFi communication
        self.sensitivity = sensitivity  # Multiplier for mouse movement sensitivity
        self.smoothing_factor = smoothing_factor  # Factor for data smoothing (0-1)
        
        # Gyroscope data storage - stores current and calibrated gyroscope readings
        self.gyro_data = {'x': 0, 'y': 0, 'z': 0}  # Current raw gyroscope data
        self.calibrated_gyro = {'x': 0, 'y': 0, 'z': 0}  # Calibrated gyroscope data
        self.calibration_offset = {'x': 0, 'y': 0, 'z': 0}  # Offset values for calibration
        self.is_calibrated = False  # Flag indicating if calibration is complete
        
        # Smoothing buffers - used to reduce jitter in gyroscope data
        self.gyro_buffer = deque(maxlen=5)  # Buffer for gyroscope data smoothing
        self.mouse_buffer = deque(maxlen=3)  # Buffer for mouse movement smoothing
        
        # Configurable scaling factors
        self.base_scale = 2.0  # Base scale factor for gyro to mouse conversion
        
        # Control flags - manage system state
        self.running = False  # Flag to control server operation
        self.mouse_enabled = True  # Flag to enable/disable mouse control
        
        # Screen dimensions - get current screen size for boundary checking
        # Use Windows API to get screen dimensions
        self.screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        self.screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        
        # Initialize socket - will be created when server starts
        self.socket = None
        
        # Thread safety - protect shared data between threads
        self.data_lock = threading.Lock()
        
        # TCP buffering - handle partial JSON messages
        self.receive_buffer = ""
        
    def start_server(self):
        """
        Start the WiFi server to receive gyroscope data from ESP8266
        
        This function creates a TCP server that listens for incoming connections from
        the ESP8266 device. It runs in the main thread and spawns separate threads
        for handling client connections and mouse control. The server continues
        running until manually stopped or an error occurs.
        """
        try:
            # Create a TCP socket for network communication
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allow socket reuse to prevent "Address already in use" errors
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind the socket to the specified host and port
            self.socket.bind((self.host, self.port))
            # Start listening for incoming connections (max 1 connection at a time)
            self.socket.listen(1)
            
            print(f"Gyroscope mouse server started on {self.host}:{self.port}")
            print("Waiting for ESP8266 connection...")
            
            # Set running flag to True to start the main loop
            self.running = True
            
            # Start mouse control thread - this runs the mouse movement logic
            # Daemon thread means it will exit when main program exits
            mouse_thread = threading.Thread(target=self._mouse_control_loop)
            mouse_thread.daemon = True
            mouse_thread.start()
            
            # Main server loop - continuously accept new connections
            while self.running:
                try:
                    # Accept incoming connection from ESP8266
                    client_socket, address = self.socket.accept()
                    print(f"Connected to ESP8266 at {address}")
                    
                    # Handle each client connection in a separate thread
                    # This allows multiple connections and prevents blocking
                    client_thread = threading.Thread(
                        target=self._handle_client, 
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    # Handle socket errors gracefully
                    if self.running:
                        print(f"Socket error: {e}")
                    break
                    
        except Exception as e:
            # Handle any unexpected errors during server startup
            print(f"Server error: {e}")
        finally:
            # Always clean up resources when server stops
            self.stop_server()
    
    def _handle_client(self, client_socket, address):
        """
        Handle incoming gyroscope data from ESP8266
        
        This function runs in a separate thread for each connected ESP8266 device.
        It continuously receives JSON data containing gyroscope readings, parses
        the data, updates the gyroscope state, and triggers calibration if needed.
        The function handles connection errors gracefully and cleans up when done.
        
        Args:
            client_socket: Socket object for communication with ESP8266
            address: Tuple containing (IP, port) of the connected device
        """
        try:
            # Main data receiving loop - continues while server is running
            while self.running:
                # Receive data from ESP8266 (max 1024 bytes)
                # Expected format: {"x": float, "y": float, "z": float}
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    # No data received means connection was closed
                    break
                
                # Add received data to buffer (handles partial messages)
                self.receive_buffer += data
                
                # Process complete JSON messages (split on newlines)
                while '\n' in self.receive_buffer:
                    # Extract one complete message
                    line, self.receive_buffer = self.receive_buffer.split('\n', 1)
                    line = line.strip()
                    
                    if not line:  # Skip empty lines
                        continue
                    
                    try:
                        # Parse the received JSON data
                        gyro_data = json.loads(line)
                        
                        # Thread-safe update of gyroscope data
                        with self.data_lock:
                            # Update current gyroscope data with new readings
                            # Convert to float and provide default value of 0 if key missing
                            self.gyro_data = {
                                'x': float(gyro_data.get('x', 0)),  # X-axis rotation
                                'y': float(gyro_data.get('y', 0)),  # Y-axis rotation  
                                'z': float(gyro_data.get('z', 0))   # Z-axis rotation
                            }
                            
                            # Add current data to smoothing buffer for noise reduction
                            self.gyro_buffer.append(self.gyro_data.copy())
                        
                        # Trigger calibration if this is the first data received
                        # Call calibration every time until it succeeds
                        if not self.is_calibrated:
                            self._calibrate_gyro()
                        
                    except json.JSONDecodeError as e:
                        # Handle malformed JSON data
                        print(f"JSON decode error: {e}")
                        print(f"Problematic data: {line}")
                    except ValueError as e:
                        # Handle invalid numeric values
                        print(f"Value error: {e}")
                        print(f"Problematic data: {line}")
                    
        except Exception as e:
            # Handle any unexpected errors during data processing
            print(f"Client handling error: {e}")
        finally:
            # Always close the connection and notify about disconnection
            client_socket.close()
            print(f"ESP8266 disconnected from {address}")
    
    def _calibrate_gyro(self):
        """
        Calibrate gyroscope to establish zero position
        
        This function calculates the average gyroscope readings from recent data
        points to establish a baseline (zero position). This is crucial because
        gyroscopes often have small offsets even when stationary. The calibration
        offset is subtracted from future readings to get accurate relative movement.
        This function is called repeatedly until enough data is available for calibration.
        """
        # Only attempt calibration if we have enough data points
        if len(self.gyro_buffer) >= 10:
            # Calculate average readings for each axis to use as calibration offset
            avg_x = sum(data['x'] for data in self.gyro_buffer) / len(self.gyro_buffer)
            avg_y = sum(data['y'] for data in self.gyro_buffer) / len(self.gyro_buffer)
            avg_z = sum(data['z'] for data in self.gyro_buffer) / len(self.gyro_buffer)
            
            # Store the calculated offsets for future use
            self.calibration_offset = {'x': avg_x, 'y': avg_y, 'z': avg_z}
            # Mark calibration as complete
            self.is_calibrated = True
            print("Gyroscope calibrated successfully!")
            print(f"Calibration offset: {self.calibration_offset}")
        else:
            # Not enough data yet, will retry on next data arrival
            print(f"Calibrating... {len(self.gyro_buffer)}/10 samples collected")
    
    def _smooth_gyro_data(self):
        """
        Apply smoothing to gyroscope data to reduce noise and jitter
        
        This function uses a weighted average of recent gyroscope readings to
        smooth out noise and provide more stable mouse movement. More recent
        data points are given higher weights to maintain responsiveness while
        still reducing unwanted jitter from sensor noise.
        
        Returns:
            dict: Smoothed gyroscope data with keys 'x', 'y', 'z'
        """
        # Return raw data if no buffer data available
        if not self.gyro_buffer:
            return self.gyro_data
        
        # Create weights that favor more recent data points
        # np.linspace creates evenly spaced values from 0.1 to 1.0
        weights = np.linspace(0.1, 1.0, len(self.gyro_buffer))
        # Normalize weights so they sum to 1.0
        weights = weights / np.sum(weights)
        
        # Calculate weighted average for each axis
        # More recent data gets higher weight, reducing noise while maintaining responsiveness
        smoothed_x = sum(data['x'] * w for data, w in zip(self.gyro_buffer, weights))
        smoothed_y = sum(data['y'] * w for data, w in zip(self.gyro_buffer, weights))
        smoothed_z = sum(data['z'] * w for data, w in zip(self.gyro_buffer, weights))
        
        return {
            'x': smoothed_x,
            'y': smoothed_y,
            'z': smoothed_z
        }
    
    def _gyro_to_mouse_delta(self, gyro_data):
        """
        Convert gyroscope data to mouse movement delta
        
        This function takes raw gyroscope data and converts it into mouse movement
        deltas (pixel changes). It applies calibration, dead zone filtering,
        sensitivity scaling, and smoothing to provide precise and stable mouse control.
        
        Args:
            gyro_data: Dictionary containing 'x', 'y', 'z' gyroscope readings
            
        Returns:
            tuple: (mouse_delta_x, mouse_delta_y) pixel movement values
        """
        # Apply calibration by subtracting the zero-position offset
        calibrated_x = gyro_data['x'] - self.calibration_offset['x']
        calibrated_y = gyro_data['y'] - self.calibration_offset['y']
        calibrated_z = gyro_data['z'] - self.calibration_offset['z']
        
        # Apply dead zone to reduce jitter from small movements
        # Values below the dead zone threshold are set to zero
        dead_zone = 0.1
        if abs(calibrated_x) < dead_zone:
            calibrated_x = 0
        if abs(calibrated_y) < dead_zone:
            calibrated_y = 0
        
        # Convert gyroscope readings to mouse pixel deltas
        # Use configurable base scale factor for fine-tuning
        mouse_delta_x = calibrated_x * self.sensitivity * self.base_scale
        mouse_delta_y = calibrated_y * self.sensitivity * self.base_scale
        
        # Apply smoothing to reduce sudden movements
        if self.mouse_buffer:
            # Get the last mouse delta for smoothing
            last_delta = self.mouse_buffer[-1]
            # Blend current delta with previous delta based on smoothing factor
            mouse_delta_x = (1 - self.smoothing_factor) * mouse_delta_x + self.smoothing_factor * last_delta[0]
            mouse_delta_y = (1 - self.smoothing_factor) * mouse_delta_y + self.smoothing_factor * last_delta[1]
        
        # Store current delta in buffer for next smoothing calculation
        self.mouse_buffer.append((mouse_delta_x, mouse_delta_y))
        
        return mouse_delta_x, mouse_delta_y
    
    def _mouse_control_loop(self):
        """
        Main mouse control loop that runs in a separate thread
        
        This function continuously processes gyroscope data and converts it to
        mouse movements. It runs at 100Hz for responsive control and includes
        boundary checking to keep the mouse within screen limits. The loop only
        processes data when the system is calibrated and mouse control is enabled.
        """
        while self.running:
            # Only process mouse movement if all conditions are met
            if self.mouse_enabled and self.is_calibrated:
                # Thread-safe access to shared data
                with self.data_lock:
                    # Check if we have data to process
                    if not self.gyro_buffer:
                        time.sleep(0.01)
                        continue
                    
                    # Get smoothed gyroscope data to reduce noise
                    smoothed_gyro = self._smooth_gyro_data()
                
                try:
                    # Convert gyroscope data to mouse movement deltas
                    delta_x, delta_y = self._gyro_to_mouse_delta(smoothed_gyro)
                    
                    # Only move mouse if the change is significant enough
                    # This prevents tiny movements from causing jitter
                    if abs(delta_x) > 0.1 or abs(delta_y) > 0.1:
                        # Get current mouse position using Windows API
                        current_x, current_y = win32api.GetCursorPos()
                        
                        # Calculate new position with boundary checking
                        # Ensure mouse stays within screen bounds
                        new_x = max(0, min(self.screen_width - 1, int(current_x + delta_x)))
                        new_y = max(0, min(self.screen_height - 1, int(current_y + delta_y)))
                        
                        # Move mouse to new position using Windows API
                        # This provides direct access to Windows mouse control
                        win32api.SetCursorPos((new_x, new_y))
                
                except Exception as e:
                    # Handle any errors in mouse control without crashing
                    print(f"Mouse control error: {e}")
            
            # Small delay to control update rate (100Hz = 10ms)
            time.sleep(0.01)
    
    def set_sensitivity(self, sensitivity):
        """
        Set mouse movement sensitivity
        
        Adjusts how much the mouse moves in response to gyroscope rotation.
        Higher values make the mouse more sensitive to small movements.
        
        Args:
            sensitivity: Sensitivity multiplier (0.1 to 5.0)
        """
        # Clamp sensitivity to reasonable range
        self.sensitivity = max(0.1, min(5.0, sensitivity))
        print(f"Sensitivity set to: {self.sensitivity}")
    
    def set_smoothing(self, factor):
        """
        Set smoothing factor for gyroscope data
        
        Controls how much smoothing is applied to reduce jitter. Lower values
        provide more smoothing but may feel less responsive.
        
        Args:
            factor: Smoothing factor (0.0 to 1.0, where 0.0 = maximum smoothing)
        """
        # Clamp smoothing factor to valid range
        self.smoothing_factor = max(0.0, min(1.0, factor))
        print(f"Smoothing factor set to: {self.smoothing_factor}")
    
    def set_base_scale(self, scale):
        """
        Set base scale factor for gyroscope to mouse conversion
        
        This controls the fundamental scaling between gyroscope readings and
        mouse pixel movement. Lower values make the mouse less sensitive,
        higher values make it more sensitive. This is multiplied by the
        sensitivity setting.
        
        Args:
            scale: Base scale factor (0.1 to 10.0)
        """
        # Clamp base scale to reasonable range
        self.base_scale = max(0.1, min(10.0, scale))
        print(f"Base scale factor set to: {self.base_scale}")
    
    def toggle_mouse(self):
        """
        Toggle mouse control on/off
        
        Allows you to temporarily disable mouse control without stopping
        the gyroscope data collection. Useful for pausing control during
        setup or when you need to use the mouse normally.
        """
        # Flip the mouse enabled flag
        self.mouse_enabled = not self.mouse_enabled
        status = "enabled" if self.mouse_enabled else "disabled"
        print(f"Mouse control {status}")
    
    def recalibrate(self):
        """
        Force recalibration of gyroscope
        
        Clears the current calibration and forces the system to recalibrate
        based on the current device position. Useful when the device has
        been moved or if calibration seems off. Hold the device steady
        after calling this function.
        """
        # Thread-safe recalibration
        with self.data_lock:
            # Reset calibration state
            self.is_calibrated = False
            # Clear all data buffers to start fresh
            self.gyro_buffer.clear()
            self.mouse_buffer.clear()
            # Clear receive buffer to start fresh
            self.receive_buffer = ""
        print("Recalibration requested. Hold device steady...")
    
    def stop_server(self):
        """
        Stop the server and cleanup resources
        
        Gracefully shuts down the WiFi server, closes all connections,
        and cleans up resources. This should be called when the program
        is exiting or when you want to stop the gyroscope mouse control.
        """
        # Set running flag to False to stop all loops
        self.running = False
        # Close the server socket if it exists
        if self.socket:
            self.socket.close()
        print("Server stopped")

def main():
    """
    Main function to run the gyroscope mouse controller
    
    This is the entry point of the program. It creates a GyroMouseController
    instance with default settings and starts the server. The program runs
    until interrupted by the user (Ctrl+C), at which point it gracefully
    shuts down all connections and resources.
    """
    print("Valorant Nerf Gun - Gyroscope Mouse Controller")
    print("=" * 50)
    
    # Create controller instance with default settings
    # host='0.0.0.0' allows connections from any IP address
    # port=12345 is the default port for ESP8266 communication
    # sensitivity=1.0 provides moderate mouse sensitivity
    # smoothing_factor=0.3 balances responsiveness with stability
    controller = GyroMouseController(
        host='0.0.0.0',
        port=12345,
        sensitivity=1.0,
        smoothing_factor=0.3
    )
    
    try:
        # Start the server - this will block until interrupted
        controller.start_server()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nShutting down...")
    finally:
        # Always clean up resources, even if interrupted
        controller.stop_server()

# Only run main() if this script is executed directly
# This allows the module to be imported without running the server
if __name__ == "__main__":
    main()