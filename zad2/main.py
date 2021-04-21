from antlr4 import *
from ctypes import CFUNCTYPE, c_double, c_int, c_byte, POINTER
from generated.LangLexer import LangLexer
from generated.LangParser import LangParser
from antlr4.error.ErrorListener import ErrorListener

from Codegen import *
import llvmlite.binding as llvm
from antlr4.tree.Trees import Trees

import argparse


def exec(module):
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()

    backing_mod = llvm.parse_assembly("")
    engine = llvm.create_mcjit_compiler(backing_mod, target_machine)

    mod = llvm.parse_assembly(str(module))
    mod.verify()
    engine.add_module(mod)
    engine.finalize_object()
    engine.run_static_constructors()

    func_ptr = engine.get_function_address("main")

    cFunc = CFUNCTYPE(c_int, c_int, POINTER(c_byte))(func_ptr)
    cFunc(0, None)

def compile(module, basename):
    llvm.initialize()
    llvm.initialize_native_asmprinter()
    llvm.initialize_native_target()

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()

    mod = llvm.parse_assembly(str(module))
    mod.verify()
    with open(f"{basename}.o" % basename, "wb") as o:
        o.write(target_machine.emit_object(mod))

def invoke_linker(basename):
    # easy solution call clang with object file
    # harder solution use ld or lld
    # import subprocess
    # subprocess.call(["ls", "-l"])
    pass


class MyErrorListener(ErrorListener):

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        global f
        printerror(f.name, line, column, msg)
        raise Exception("syntax")


def printerror(name, line, column, msg):
    print(name + ":" + str(line) + ":" + str(column) + ": " + "error: " + msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='My super lang compiler')
    parser.add_argument('--ast', action="store_true", dest="ast", default=False)
    parser.add_argument('--ir', action="store_true", dest="ir", default=False)
    parser.add_argument('--run', action="store_true", dest="run", default=False)
    parser.add_argument('-o', action="store", dest="ouput", default="a.out")
    parser.add_argument('file', type=argparse.FileType('r'), nargs='+')

    args = parser.parse_args()

    if len(args.file) > 1:
        print("Multiple files not supported yet :(")
        quit()

    f =  args.file[0] #open(args.file[0], "r")
    txt = f.read()

    lexer = LangLexer(InputStream(txt))
    stream = CommonTokenStream(lexer)
    parser = LangParser(stream)

    parser.removeErrorListeners()
    parser.addErrorListener(MyErrorListener())

    try:
        tree = parser.program()
    except Exception:
        quit()

    if args.ast:
        print(Trees.toStringTree(tree, None, parser))
        print()
        quit()

    codegen = Codegen()

    try:
        ir = codegen.gen_ir(tree)
    except CodegenException as ex:
        printerror(f.name, ex.line, ex.column, ex.msg)
        print(txt.splitlines()[ex.line-1])
        print(" " * ex.column + "↑")
        quit()

    if args.ir:
        print(str(ir))
        quit()

    if args.run:
        exec(ir)
    else:
        # compile to file
        print("Compile not ready yet :(")
        pass