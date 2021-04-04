from antlr4 import *
from ctypes import CFUNCTYPE, c_double, c_int, POINTER
from generated.CalcLexer import CalcLexer
from generated.CalcParser import CalcParser

from Codegen import *
import llvmlite.binding as llvm
from antlr4.tree.Trees import Trees

def exec(module):
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()

    backing_mod = llvm.parse_assembly("")
    engine = llvm.create_mcjit_compiler(backing_mod, target_machine)

    mod = llvm.parse_assembly(str(module))
    engine.add_module(mod)
    engine.finalize_object()
    engine.run_static_constructors()

    func_ptr = engine.get_function_address("main")

    cFunc = CFUNCTYPE(c_int, c_int, POINTER(c_int))(func_ptr)
    cFunc(0, None)

def magic(txt):
    lexer = CalcLexer(InputStream(txt))
    stream = CommonTokenStream(lexer)
    parser = CalcParser(stream)
    tree = parser.program()

    print(Trees.toStringTree(tree, None, parser))

    print()

    codegen = Codegen()
    ir = codegen.gen_ir(tree)
    print(str(ir))
    exec(ir)


f = open("test.pclang", "r")
txt = f.read()
magic(txt)
'''
while(True):
    print(">>>", end="")
    magic(input())'''