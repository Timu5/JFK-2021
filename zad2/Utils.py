from llvmlite import ir


class CodegenException(Exception):
    def __init__(self, start, msg):
        self.line = start.line
        self.column = start.column
        self.msg = msg
        super().__init__(self.msg)


class UnsignedType(ir.IntType):
    pass


class SignedType(ir.IntType):
    pass


int_ = SignedType(32)
uint = UnsignedType(32)
long_ = SignedType(64)
ulong = UnsignedType(64)
short_ = SignedType(16)
ushort = UnsignedType(16)
byte_ = SignedType(8)
ubyte = UnsignedType(8)

voidptr = ir.IntType(8).as_pointer()


class SizedArrayType(ir.LiteralStructType):
    def __init__(self, element_type):
        super().__init__([ulong, ir.ArrayType(element_type, 1).as_pointer()])
        self.element = element_type


class StringType(ir.LiteralStructType):
    def __init__(self):
        super().__init__([ulong, ir.ArrayType(ubyte, 1).as_pointer()])
        self.element = ubyte


def isNumber(x):
    if isinstance(x.type, ir.IntType) or isinstance(x.type, ir.types._BaseFloatType):
        return True
    return False


def isUnsgined(x):
    if isinstance(x.type, UnsignedType):
        return True
    return False


def isSigned(x):
    if isinstance(x.type, SignedType):
        return True
    return False
