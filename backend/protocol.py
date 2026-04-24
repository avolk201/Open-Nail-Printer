class Protocol:
    START_PRINT = b'\x01'
    READY = b'\x02'
    SEND_LINE = b'\x03'
    LINE_ACK = b'\x04'
