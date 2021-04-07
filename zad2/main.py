from antlr4 import *
from ctypes import CFUNCTYPE, c_double, c_int, c_byte, POINTER
from generated.CalcLexer import CalcLexer
from generated.CalcParser import CalcParser
from antlr4.error.ErrorListener import ErrorListener

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

    cFunc = CFUNCTYPE(c_int, c_int, POINTER(c_byte))(func_ptr)
    cFunc(0, None)


class MyErrorListener(ErrorListener):

    def __init__(self):
        super(MyErrorListener, self).__init__()

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        printerror(line, column, msg)
        raise Exception("syntax")


def printerror(line, column, msg):
    print("file:" + str(line) + ":" + str(column) + ": " + "error: " + msg)


def magic(txt):
    lexer = CalcLexer(InputStream(txt))
    stream = CommonTokenStream(lexer)
    parser = CalcParser(stream)

    parser.removeErrorListeners()
    parser.addErrorListener(MyErrorListener())

    try:
        tree = parser.program()
    except Exception:
        return

    print(Trees.toStringTree(tree, None, parser))

    print()

    codegen = Codegen()

    try:
        ir = codegen.gen_ir(tree)
        print(str(ir))
        exec(ir)
    except CodegenException as ex:
        printerror(ex.line, ex.column, ex.msg)


f = open("test.pclang", "r")
txt = f.read()
magic(txt)
'''
while(True):
    print(">>>", end="")
    magic(input())'''
