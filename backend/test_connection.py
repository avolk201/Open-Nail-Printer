import serial
import serial.tools.list_ports
import time
import sys
from protocol import Protocol

# PRINTCART_NOZDATA_SZ is 42 bytes (14 nozzles * 3 colors)
NOZDATA_SZ = 42

def find_esp32_port():
    """Find the USB serial port for the ESP32."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "usbserial" in port.device.lower() or "usbmodem" in port.device.lower() or "ttyusb" in port.device.lower():
            return port.device
    
    # Fallback to the first available port if none match typical USB serial names
    if ports:
        return ports[0].device
    return None

def test_connection():
    port_name = find_esp32_port()
    if not port_name:
        print("❌ Could not find any USB serial ports. Is the ESP32 plugged in?")
        sys.exit(1)

    print(f"🔌 Connecting to ESP32 on {port_name} at 921600 baud...")
    
    try:
        # The ESP32 might restart when the serial port is opened (DTR/RTS)
        ser = serial.Serial(port_name, 921600, timeout=2)
        print("⏳ Waiting 2 seconds for ESP32 to boot...")
        time.sleep(2)
        
        # Clear any startup logs from the buffer
        ser.reset_input_buffer()
        
        print("\n[TEST 1] Sending START_PRINT command (0x01)...")
        ser.write(Protocol.START_PRINT)
        
        response = ser.read(1)
        if response == Protocol.READY:
            print("✅ Received READY (0x02) from ESP32!")
        else:
            print(f"❌ Failed to receive READY. Got: {response}")
            sys.exit(1)

        print(f"\n[TEST 2] Sending SEND_LINE command (0x03) with {NOZDATA_SZ} bytes of dummy data...")
        dummy_data = bytes([0xAA] * NOZDATA_SZ)
        ser.write(Protocol.SEND_LINE + dummy_data)
        
        response = ser.read(1)
        if response == Protocol.LINE_ACK:
            print("✅ Received LINE_ACK (0x04) from ESP32!")
        else:
            print(f"❌ Failed to receive LINE_ACK. Got: {response}")
            sys.exit(1)

        print("\n🎉 Connection test passed! The Python backend can successfully talk to the ESP32 firmware.")
        ser.close()

    except Exception as e:
        print(f"❌ Error communicating with ESP32: {e}")

if __name__ == "__main__":
    test_connection()
