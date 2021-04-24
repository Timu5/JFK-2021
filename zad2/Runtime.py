from llvmlite import ir
import llvmlite.binding as llvm
from Utils import *


def get_runtime_functions(module):

    runtime = {}

    runtime["GC_init"] = ir.Function(
        module, ir.FunctionType(ir.VoidType(), []), name="GC_init")
    runtime["GC_deinit"] = ir.Function(
        module, ir.FunctionType(ir.VoidType(), []), name="GC_deinit")
    runtime["GC_malloc"] = ir.Function(module, ir.FunctionType(
        voidptr, [ulong]), name="GC_malloc")
    runtime["GC_malloc_atomic"] = ir.Function(module, ir.FunctionType(
        voidptr, [ulong]), name="GC_malloc_atomic")
    runtime["GC_free"] = ir.Function(module, ir.FunctionType(
        ir.VoidType(), [voidptr]), name="GC_free")

    runtime["array_add"] = ir.Function(module, ir.FunctionType(SizedArrayType(int_), [
                                       SizedArrayType(int_), SizedArrayType(int_), ulong, ir.FunctionType(
                                           voidptr, [ulong]).as_pointer()]), name="array_add")

    runtime["string_add"] = ir.Function(module, ir.FunctionType(StringType(), [StringType(), StringType(), ir.FunctionType(voidptr, [ulong]).as_pointer()]), name="string_add")

    return runtime
