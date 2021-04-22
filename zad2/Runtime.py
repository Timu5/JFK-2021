from llvmlite import ir
import llvmlite.binding as llvm
from Utils import *


def get_runtime_functions(module):

    runtime = {}

    voidptr_ty = ir.IntType(8).as_pointer()

    runtime["GC_init"] = ir.Function(
        module, ir.FunctionType(ir.VoidType(), []), name="GC_init")
    runtime["GC_deinit"] = ir.Function(
        module, ir.FunctionType(ir.VoidType(), []), name="GC_deinit")
    runtime["GC_malloc"] = ir.Function(module, ir.FunctionType(
        voidptr_ty, [SignedType(64, False)]), name="GC_malloc")
    runtime["GC_malloc_atomic"] = ir.Function(module, ir.FunctionType(
        voidptr_ty, [SignedType(64, False)]), name="GC_malloc_atomic")
    runtime["GC_free"] = ir.Function(module, ir.FunctionType(
        ir.VoidType(), [voidptr_ty]), name="GC_free")

    runtime["array_add"] = ir.Function(module, ir.FunctionType(SizedArrayType(SignedType(32, True)), [
                                       SizedArrayType(SignedType(32, True)), SizedArrayType(SignedType(32, True)), SignedType(64, False), ir.FunctionType(
                                           voidptr_ty, [SignedType(64, False)]).as_pointer()]), name="array_add")

    return runtime
