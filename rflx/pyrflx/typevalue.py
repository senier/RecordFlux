from abc import ABC, abstractmethod, abstractproperty
from typing import Any, Mapping

from rflx.common import generic_repr
from rflx.expression import TRUE, Expr, Name, Variable
from rflx.model import Enumeration, Integer, Number, Opaque, Scalar, Type

class NotInitializedError(Exception):
    pass

class TypeValue(ABC):

    _value: Any = None

    def __init__(self, vtype: Type) -> None:
        self._type = vtype

    def __repr__(self) -> str:
        return generic_repr(self.__class__.__name__, self.__dict__)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return self._value == other._value and self._type == other._type
        return NotImplemented

    @property
    def initialized(self) -> bool:
        return self._value is not None

    def _raise_initialized(self) -> None:
        if not self.initialized:
            raise NotInitializedError("value not initialized")

    def clear(self) -> None:
        self._value = None

    @abstractmethod
    def assign(self, value: Any, check: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def assign_bitvalue(self, value: Any, check: bool) -> None:
        raise NotImplementedError

    @abstractproperty
    def value(self) -> Any:
        raise NotImplementedError

    @abstractproperty
    def binary(self) -> str:
        raise NotImplementedError

    @abstractproperty
    def accepted_type(self) -> type:
        raise NotImplementedError

    @abstractproperty
    def literals(self) -> Mapping[Name, Expr]:
        raise NotImplementedError

    @classmethod
    def construct(cls, vtype: Type) -> "TypeValue":
        if isinstance(vtype, Integer):
            return IntegerValue(vtype)
        if isinstance(vtype, Enumeration):
            return EnumValue(vtype)
        if isinstance(vtype, Opaque):
            return OpaqueValue(vtype)
        raise ValueError("cannot construct unknown type: " + type(vtype).__name__)

    @staticmethod
    def convert_bytes_to_bitstring(msg: bytes) -> str:
        binary_repr: str = ""

        for i in range(0, len(msg)):
            b = bin(msg[i]).lstrip('0b')
            b = b.zfill(8)

            binary_repr = binary_repr + b

        return binary_repr

    @staticmethod
    def convert_bits_to_integer(bitstring: str) -> int:

        # Todo: Methode vereinfachen
        data_for_nxt_field_int = []
        j = 0
        for i in range(len(bitstring), 0, -1):
            data_for_nxt_field_int.append(int(bitstring[i - 1]) * 2 ** j)
            j += 1

        d = 0
        for i in range(0, len(data_for_nxt_field_int)):
            d = d + data_for_nxt_field_int[i]

        return d


class ScalarValue(TypeValue):

    _type: Scalar

    def __init__(self, vtype: Scalar) -> None:
        super().__init__(vtype)

    @abstractproperty
    def expr(self) -> Expr:
        return NotImplemented

    @abstractproperty
    def literals(self) -> Mapping[Name, Expr]:
        raise NotImplementedError

    @property
    def size(self) -> int:
        size_expr = self._type.size.simplified()
        assert isinstance(size_expr, Number)
        return size_expr.value


class IntegerValue(ScalarValue):

    _value: int
    _type: Integer

    def __init__(self, vtype: Integer) -> None:
        super().__init__(vtype)

    @property
    def _first(self) -> int:
        first = self._type.first.simplified()
        assert isinstance(first, Number)
        return first.value

    @property
    def _last(self) -> int:
        last = self._type.last.simplified()
        assert isinstance(last, Number)
        return last.value

    def assign(self, value: int, check: bool = True) -> None:
        if (
            self._type.constraints("__VALUE__", check).simplified(
                {Variable("__VALUE__"): Number(value)}
            )
            != TRUE
        ):
            raise ValueError(f"value {value} not in type range {self._first} .. {self._last}")
        self._value = value

    def assign_bitvalue(self, value: str, check: bool = True) -> None:

        for i in range(0, len(value)):
            if value[i] not in {'0', '1'}:
                raise ValueError("String is not a bitstring: only 0 and 1 allowed")

        self.assign(self.convert_bits_to_integer(value))


    @property
    def expr(self) -> Number:
        self._raise_initialized()
        return Number(self._value)

    @property
    def value(self) -> int:
        self._raise_initialized()
        return self._value

    @property
    def binary(self) -> str:
        self._raise_initialized()
        return format(self._value, f"0{self.size}b")

    @property
    def accepted_type(self) -> type:
        return int

    @property
    def literals(self) -> Mapping[Name, Expr]:
        return {}


class EnumValue(ScalarValue):

    _value: str
    _type: Enumeration

    def __init__(self, vtype: Enumeration) -> None:
        super().__init__(vtype)

    def assign(self, value: str, check: bool = True) -> None:
        if value not in self._type.literals:
            raise KeyError(f"{value} is not a valid enum value")
        assert (
            self._type.constraints("__VALUE__", check).simplified(
                {
                    **{Variable(k): v for k, v in self._type.literals.items()},
                    **{Variable("__VALUE__"): self._type.literals[value]},
                }
            )
            == TRUE
        )
        self._value = value

    def assign_bitvalue(self, value: str, check: bool = True) -> None:
        #  check ob ein bit string übergeben wurde
        for i in range(0, len(value)):
            if value[i] not in {'0', '1'}:
                b= value[i]
                raise ValueError("String is not a bitstring: only 0 and 1 allowed")

        value_as_int: int = self.convert_bits_to_integer(value)

        # check ob bitstring (als int) ein valides enum value ist -> in dem Falle muss das EnumValue eine Zahl sein,
        # weil ein String nicht in ein Paket geschrieben werden kann
        if not Number(value_as_int) in self.literals.values():
            raise KeyError(f"Number {value_as_int} is not a valid enum value")

        self._value = value

    @property
    def value(self) -> str:
        self._raise_initialized()
        return self._value

    @property
    def expr(self) -> Variable:
        self._raise_initialized()
        return Variable(self._value)

    @property
    def binary(self) -> str:
        self._raise_initialized()
        return format(self._type.literals[self._value].value, f"0{self.size}b")

    @property
    def accepted_type(self) -> type:
        return str

    @property
    def literals(self) -> Mapping[Name, Expr]:
        return {Variable(k): v for k, v in self._type.literals.items()}


class OpaqueValue(TypeValue):

    _value: bytes

    def __init__(self, vtype: Opaque) -> None:
        super().__init__(vtype)

    def assign(self, value: bytes, check: bool = True) -> None:
        self._value = value

    def assign_bitvalue(self, bits: str, check: bool = True) -> None:

        for i in range(0, len(bits)):
            if bits[i] not in {'0', '1'}:
                b= bits[i]
                raise ValueError("String is not a bitstring: only 0 and 1 allowed")

        # ist der bitstring druch 8 teilbar?
        while len(bits) % 8 != 0:
            # wenn nicht, dann fülle vorne mit 0 auf
            bits = '0' + bits

        # convertierte bitstring wieder in bytes
        bytestring = b"".join(
            [int(bits[i: i + 8], 2).to_bytes(1, "big") for i in range(0, len(bits), 8)])

        self._value = bytestring

    @property
    def length(self) -> int:
        self._raise_initialized()
        return len(self._value) * 8

    @property
    def value(self) -> bytes:
        self._raise_initialized()
        return self._value

    @property
    def binary(self) -> str:
        self._raise_initialized()
        return format(int.from_bytes(self._value, "big"), f"0{self.length}b")

    @property
    def accepted_type(self) -> type:
        return bytes

    @property
    def literals(self) -> Mapping[Name, Expr]:
        return {}



