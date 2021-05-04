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

half_ = ir.HalfType()
float_ = ir.FloatType()
double_ = ir.DoubleType()

voidptr = ir.IntType(8).as_pointer()


class SizedArrayType(ir.LiteralStructType):
    def __init__(self, element_type):
        super().__init__([ulong, ir.ArrayType(element_type, 1).as_pointer()])
        self.element = element_type


class StringType(ir.LiteralStructType):
    def __init__(self):
        super().__init__([ulong, ir.ArrayType(ubyte, 1).as_pointer()])
        self.element = ubyte

class StructType:
    def __init__(self, name, members, indexes, fields, isclass=False):
        self.name = name
        self.members = members
        self.indexes = indexes
        self.isclass = isclass
        self.fields = fields
        self.fullname = name

class ClassType(ir.PointerType):
    def __init__(self, name, el, struct):
        super().__init__(el)
        self.name = name
        self.struct = struct

class StructMethod:
    def __init__(self, obj, fn):
        self.obj = obj
        self.fn = fn

class FunctionTemplate:
    def __init__(self, body, types):
        self.body = body
        self.types = types
        self.implemented = {}

class StructTemplate:
    def __init__(self, body, types):
        self.body = body
        self.types = types
        self.implemented = {}

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

def isClass(x):
    if x.type.is_pointer and isinstance(x.type.pointee, ir.IdentifiedStructType):
        return True
    return False

def isStruct(x):
    if isinstance(x.type, ir.IdentifiedStructType):
        return True
    return False

def isClassOrStruct(x):
    if isStruct(x):
        return True
    if isClass(x):
        return True
    return False

def type2str(typ):
    if typ == int_:
        return "int"
    elif typ == uint:
        return "uint"
    elif typ == long_:
        return "long"
    elif typ == ulong:
        return "ulong"
    elif typ == short_:
        return "short"
    elif typ == ushort:
        return "ushort"
    elif typ == byte_:
        return "byte"
    elif typ == ubyte:
        return "ubyte"
    elif typ == half_:
        return "half"
    elif typ == float_:
        return "float"
    elif typ == double_:
        return "double"
    elif typ == ir.VoidType():
        return "void"

    elif isinstance(typ, StringType):
        return "string"

    elif isinstance(typ, SizedArrayType):
        return type2str(typ.element) + "[]"

    elif isinstance(typ, ClassType) or isinstance(typ, ir.IdentifiedStructType):
        if typ.name[0] == "$":
            return typ.fullname
        return typ.name

    elif isinstance(typ, ir.PointerType):
        return type2str(typ.pointee) + "*"

    elif isinstance(typ, ir.FunctionType):
        # TODO: var args 
        return "f(" + ','.join(map(lambda x: type2str(x), typ.args)) + ")->" + type2str(typ.return_type)

    return "?"
