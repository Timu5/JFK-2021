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

