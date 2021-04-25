from antlr4 import *
from ctypes import CFUNCTYPE, c_double, c_int, c_byte, POINTER
from generated.LangLexer import LangLexer
from generated.LangParser import LangParser
from antlr4.error.ErrorListener import ErrorListener

from Codegen import Codegen
from Utils import CodegenException
import llvmlite.binding as llvm
from antlr4.tree.Trees import Trees

import argparse

target = None
target_machine = None

files = []


def llvm_init():
    global target, target_machine
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    #llvm.load_library_permanently("gc.dll")
    #llvm.load_library_permanently("runtime.dll")

    llvm.load_library_permanently("./runtime/build/bdwgc/libgc.so")
    llvm.load_library_permanently("./runtime/build/libruntime.so")

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()


def exec(module):
    global target_machine
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
    global target_machine
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
        printerror(line, column, msg)
        raise Exception("syntax")


def printerror(line, column, msg):
    global files
    name = files[-1]
    print(name + ":" + str(line) + ":" + str(column) + ": " + "error: " + msg)
    with open(name, 'r') as f:
        txt = f.readlines()
        print(txt[line-1][:-1])
        print(" " * column + "↑")


def parse_text(txt):
    lexer = LangLexer(InputStream(txt))
    lexer.removeErrorListeners()
    lexer.addErrorListener(MyErrorListener())

    stream = CommonTokenStream(lexer)
    
    parser = LangParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(MyErrorListener())

    try:
        tree = parser.program()
    except Exception:
        print("konczymy")
        quit()

    return tree


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='My super lang compiler')
    parser.add_argument('--ast', action="store_true",
                        dest="ast", default=False)
    parser.add_argument('--ir', action="store_true", dest="ir", default=False)
    parser.add_argument('--run', action="store_true",
                        dest="run", default=False)
    parser.add_argument('-o', action="store", dest="ouput", default="a.out")
    parser.add_argument('file', type=argparse.FileType('r'), nargs='+')

    args = parser.parse_args()

    if len(args.file) > 1:
        print("Multiple files not supported yet :(")
        quit()

    f = args.file[0]
    txt = f.read()

    files.append(f.name)

    tree = parse_text(txt)

    if args.ast:
        print(Trees.toStringTree(tree, None, parser))
        print()
        quit()

    llvm_init()

    codegen = Codegen(target_machine)

    try:
        ir = codegen.gen_ir(tree)
    except CodegenException as ex:
        printerror(ex.line, ex.column, ex.msg)
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

    files.pop()
