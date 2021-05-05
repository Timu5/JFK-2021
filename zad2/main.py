from antlr4 import *
from ctypes import CFUNCTYPE, c_double, c_int, c_byte, POINTER
from generated.LangLexer import LangLexer
from generated.LangParser import LangParser
from antlr4.error.ErrorListener import ErrorListener

import Codegen
from Utils import CodegenException
import llvmlite.binding as llvm
from antlr4.tree.Trees import Trees

import argparse

class MyErrorListener(ErrorListener):

    def __init__(self, driver):
        self.driver = driver

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.driver.printerror(line, column, msg)
        raise Exception("syntax")

class Driver:
    def __init__(self):
        self.target = None
        self.target_machine = None
        self.files = []


    def llvm_init(self):
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()

        self.target = llvm.Target.from_default_triple()
        self.target_machine = self.target.create_target_machine()


    def exec(self, module):
        backing_mod = llvm.parse_assembly("")
        engine = llvm.create_mcjit_compiler(backing_mod, self.target_machine)

        mod = llvm.parse_assembly(str(module))
        mod.verify()
        engine.add_module(mod)
        engine.finalize_object()
        engine.run_static_constructors()

        func_ptr = engine.get_function_address("main")

        cFunc = CFUNCTYPE(c_int, c_int, POINTER(c_byte))(func_ptr)
        cFunc(0, None)


    def compile(self, module, basename):
        mod = llvm.parse_assembly(str(module))
        mod.verify()
        with open(f"{basename}.o", "wb") as o:
            o.write(self.target_machine.emit_object(mod))


    def invoke_linker(self, basename):
        # easy solution call clang with object file
        # harder solution use ld or lld

        # import subprocess
        # subprocess.call(["clang", "a", "b"])
        pass


    def printerror(self, line, column, msg):
        #print(self.files)
        name = self.files[-1]
        print(name + ":" + str(line) + ":" + str(column) + ": " + "error: " + msg)
        with open(name, 'r') as f:
            txt = f.readlines()
            print(txt[line-1][:-1])
            print(" " * column + "↑")

    def compile_file(self, filename, target_machine):
        with open(filename) as f:
            self.files.append(f.name)
            tree, parser_ = self.parse_text(f.read())
            codegen = Codegen.Codegen(self, target_machine)
            module = codegen.gen_ir(tree)
            self.files.pop()
            return module

    def parse_text(self, txt):
        lexer = LangLexer(InputStream(txt))
        lexer.removeErrorListeners()
        lexer.addErrorListener(MyErrorListener(self))

        stream = CommonTokenStream(lexer)
        
        parser = LangParser(stream)
        parser.removeErrorListeners()
        parser.addErrorListener(MyErrorListener(self))

        try:
            tree = parser.program()
        except Exception:
            quit()

        return tree, parser

    def main(self):
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

        self.files.append(f.name)

        tree, parser_ = self.parse_text(txt)

        if args.ast:
            print(Trees.toStringTree(tree, None, parser_))
            print()
            quit()

        self.llvm_init()

        codegen = Codegen.Codegen(self, self.target_machine)

        try:
            ir = codegen.gen_ir(tree)
        except CodegenException as ex:
            self.printerror(ex.line, ex.column, ex.msg)
            quit()

        if args.ir:
            print(str(ir))
            quit()

        if args.run:
            llvm.load_library_permanently("./runtime/build/bdwgc/libgc.so")
            llvm.load_library_permanently("./runtime/build/libruntime.so")
            self.exec(ir)
        else:
            # compile to file
            self.compile(ir, "./" + self.files[-1])
            pass

        self.files.pop()

if __name__ == "__main__":
    drv = Driver()
    drv.main()