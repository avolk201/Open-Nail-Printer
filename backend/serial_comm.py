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
        self.last_cmd = None
        logger.info(f"Mock Serial initialized on {port} at {baudrate} baud.")

    async def write_async(self, data: bytes):
        logger.debug(f"Serial WRITE: {data}")
        if data and len(data) > 0:
            self.last_cmd = data[0:1]
        await asyncio.sleep(0.01) # Simulate transmission delay

    async def read_async(self, num_bytes: int) -> bytes:
        await asyncio.sleep(0.01)
        if self.last_cmd in (Protocol.START_PRINT, Protocol.HOME):
            return Protocol.READY * num_bytes
        elif self.last_cmd == Protocol.SEND_LINE:
            return Protocol.LINE_ACK * num_bytes
        return b'\x00' * num_bytes

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
        response = await self.connection.read_async(1)
        if response == Protocol.READY:
            logger.info("Received READY from ESP32")
            return True
        else:
            logger.error(f"Failed to receive READY from ESP32, got: {response}")
            return False

    async def send_line(self, byte_array: bytes, max_retries: int = 3):
        for _ in range(max_retries):
            await self.connection.write_async(Protocol.SEND_LINE + byte_array)
            response = await self.connection.read_async(1)
            if response == Protocol.LINE_ACK:
                return True
            elif response == Protocol.LINE_NACK:
                logger.warning("Received NACK from ESP32, retrying...")
                await asyncio.sleep(0.01)
                continue
            else:
                logger.error(f"Unexpected response from ESP32: {response}")
                return False
        logger.error("Max retries reached for send_line")
        return False

    async def home(self):
        logger.info("Sending HOME to ESP32")
        await self.connection.write_async(Protocol.HOME)
        response = await self.connection.read_async(1)
        if response == Protocol.READY:
            logger.info("Received READY from ESP32 for HOME")
            return True
        else:
            logger.error(f"Failed to receive READY from ESP32 for HOME, got: {response}")
            return False
