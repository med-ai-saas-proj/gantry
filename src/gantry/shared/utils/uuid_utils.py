from uuid import UUID

import fastuuid


__all__ = [
    "uuid7",
]


# def uuid7() -> UUID:
#     """Generate uuid V7."""
#     return UUID(bytes=fastuuid.uuid7().bytes)

import os
import time
import uuid
import threading


class UUIDv7SubMsGenerator:
    """
    UUIDv7 monotonic generator using:

    - 48-bit unix timestamp in milliseconds
    - 12-bit sub-millisecond fraction
    - 62-bit monotonic sequence/random field

    Layout:

    | 48b unix_ms | 4b ver | 12b subms | 2b variant | 62b rand/seq |

    The 12-bit subms field stores fractional millisecond precision:
        subms = (nanoseconds % 1_000_000) * 4096 / 1_000_000

    Monotonic guarantees:
    - lexicographically sortable
    - strictly increasing within same timestamp/subms
    - clock rollback resistant
    """

    def __init__(self):
        self._lock = threading.Lock()

        self._last_ms = 0
        self._last_subms = 0
        self._seq = 0

        self._max_seq = (1 << 62) - 1

    @staticmethod
    def _current_time():
        ns = time.time_ns()

        ms = ns // 1_000_000
        sub_ns = ns % 1_000_000

        # convert fractional ms -> 12-bit value
        subms = (sub_ns * 4096) // 1_000_000

        if subms > 0xFFF:
            subms = 0xFFF

        return ms, subms

    def generate(self) -> uuid.UUID:
        with self._lock:
            ms, subms = self._current_time()

            # monotonic timestamp handling
            if ms > self._last_ms or (
                ms == self._last_ms and subms > self._last_subms
            ):
                self._last_ms = ms
                self._last_subms = subms

                # fresh random sequence
                self._seq = int.from_bytes(os.urandom(8), "big") & self._max_seq

            else:
                # clock same/backwards
                ms = self._last_ms
                subms = self._last_subms

                self._seq += 1

                if self._seq > self._max_seq:
                    # wait until clock advances
                    while True:
                        nms, nsub = self._current_time()

                        if nms > self._last_ms or (
                            nms == self._last_ms and nsub > self._last_subms
                        ):
                            self._last_ms = nms
                            self._last_subms = nsub

                            ms = nms
                            subms = nsub

                            self._seq = (
                                int.from_bytes(os.urandom(8), "big")
                                & self._max_seq
                            )
                            break

            # Build UUID integer
            value = 0

            # 48-bit unix timestamp ms
            value |= (ms & ((1 << 48) - 1)) << 80

            # version 7
            value |= 0x7 << 76

            # 12-bit subms fraction
            value |= (subms & 0xFFF) << 64

            # variant RFC4122/9562 (10xx)
            value |= 0b10 << 62

            # 62-bit sequence/random
            value |= self._seq

            return uuid.UUID(int=value)


# global singleton
_uuid7_gen = UUIDv7SubMsGenerator()


def uuid7() -> uuid.UUID:
    return _uuid7_gen.generate()
