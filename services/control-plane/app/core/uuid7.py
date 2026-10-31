import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """Generate a UUIDv7 (RFC 9562) with milliseconds timestamp and random bits.
    Falls back to uuid.uuid7() if supported by the Python runtime (3.13+).
    """
    if hasattr(uuid, "uuid7"):
        return getattr(uuid, "uuid7")()

    # 48-bit timestamp in milliseconds
    ms = int(time.time() * 1000)
    rand_bytes = os.urandom(10)

    b = bytearray(16)
    b[0:6] = ms.to_bytes(6, byteorder="big")
    # 4-bit version 7 + 12-bit rand_a
    b[6] = 0x70 | (rand_bytes[0] & 0x0F)
    b[7] = rand_bytes[1]
    # 2-bit variant (10xx) + 62-bit rand_b
    b[8] = 0x80 | (rand_bytes[2] & 0x3F)
    b[9:16] = rand_bytes[3:10]

    return uuid.UUID(bytes=bytes(b))

