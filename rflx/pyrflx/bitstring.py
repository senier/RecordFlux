from typing import Union


class Bitstring:

    _bits: str

    def __init__(self, bits: str = ""):
        if not self.check_bitstring(bits):
            raise ValueError("Bitstring does not consist of only 0 and 1")
        self._bits = bits

    def __add__(self, other: "Bitstring") -> "Bitstring":
        return Bitstring(self._bits + other._bits)

    def __iadd__(self, other: "Bitstring") -> "Bitstring":
        self._bits += other._bits
        return self

    def __getitem__(self, key: Union[int, slice]) -> "Bitstring":
        return Bitstring(self._bits[key])

    def __str__(self):
        return self._bits

    def __int__(self):
        return int(self._bits, 2)

    def from_bytes(self, msg: bytes) -> "Bitstring":
        self._bits = format(int.from_bytes(msg, "big"), f"0{len(msg) * 8}b")
        return self

    @staticmethod
    def check_bitstring(bitstring: str) -> bool:

        for bit in bitstring:
            if bit not in ["0", "1"]:
                return False

        return True

    @staticmethod
    def convert_bytes_to_string(msg: bytes) -> str:
        return format(int.from_bytes(msg, "big"), f"0{len(msg) * 8}b")
