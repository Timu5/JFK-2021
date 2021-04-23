from llvmlite import ir


class CodegenException(Exception):
    def __init__(self, start, msg):
        self.line = start.line
        self.column = start.column
        self.msg = msg
        super().__init__(self.msg)


class SignedType(ir.IntType):
    def __new__(cls, value, *args, **kwargs):
        return ir.IntType.__new__(cls, value)

    def __init__(self, size, signed):
        self.is_signed = signed
        self.is_unsigned = not signed


class SizedArrayType(ir.LiteralStructType):
    def __init__(self, element_type):
        super().__init__([SignedType(64, False),
                          ir.ArrayType(element_type, 1).as_pointer()])

class StringType(ir.LiteralStructType):
    def __init__(self):
        super().__init__([SignedType(64, False),
                          ir.ArrayType(SignedType(8, False), 1).as_pointer()])


def isNumber(x):
    if isinstance(x.type, ir.IntType) or isinstance(x.type, ir.types._BaseFloatType):
        return True
    return False
