import asyncio
import logging
from protocol import Protocol

logger = logging.getLogger(__name__)

class SerialMock:
    """Mock serial connection for local testing on Mac."""
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.is_open = True
        logger.info(f"Mock Serial initialized on {port} at {baudrate} baud.")

    async def write_async(self, data: bytes):
        logger.debug(f"Serial WRITE: {data}")
        await asyncio.sleep(0.01) # Simulate transmission delay

    async def read_async(self, num_bytes: int) -> bytes:
        await asyncio.sleep(0.01)
        # Mocking ESP32 acknowledging a line or being ready
        return Protocol.LINE_ACK * num_bytes

class SerialManager:
    def __init__(self, port="/dev/ttyUSB0", baudrate=921600, mock=True):
        self.mock = mock
        if self.mock:
            self.connection = SerialMock(port, baudrate)
        else:
            import serial
            class AsyncSerial:
                def __init__(self, p, b):
                    self.ser = serial.Serial(p, b, timeout=1)
                async def write_async(self, data):
                    self.ser.write(data)
                async def read_async(self, num_bytes):
                    return self.ser.read(num_bytes)
            self.connection = AsyncSerial(port, baudrate)

    async def start_print(self):
        logger.info("Sending START_PRINT to ESP32")
        await self.connection.write_async(Protocol.START_PRINT)
        # Wait for READY

    async def send_line(self, byte_array: bytes):
        await self.connection.write_async(Protocol.SEND_LINE + byte_array)
        response = await self.connection.read_async(1)
        if response == Protocol.LINE_ACK:
            return True
        return False

    async def home(self):
        logger.info("Sending HOME to ESP32")
        await self.connection.write_async(Protocol.HOME)
        # Assuming mock is ready
        return True
