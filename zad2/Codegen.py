from llvmlite import ir
from antlr4 import *
from generated.CalcLexer import CalcLexer
from generated.CalcVisitor import CalcVisitor
from generated.CalcParser import CalcParser

class Codegen(CalcVisitor):

    def __init__(self):
        self.builder = None
        self.module = None
        #self.printf = None
        self.locals = {}


    def gen_ir(self, node):
        # Create an empty module...
        self.module = ir.Module(name="my_super_modul")

        #printf_ty = ir.FunctionType(ir.IntType(32), [ir.IntType(8).as_pointer()], var_arg=True)
        #self.printf = ir.Function(self.module, printf_ty, name="printf")

        fnty = ir.FunctionType(ir.VoidType(), [])
        func = ir.Function(self.module, fnty, name="start")

        # Now implement the function
        block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

        self.visit(node)
        self.builder.ret_void()

        return self.module

    def visitNumber(self, ctx:CalcParser.NumberContext):
        return ir.Constant(ir.IntType(32), int(ctx.getText()))

    def visitFloat(self, ctx:CalcParser.FloatContext):
        return ir.Constant(ir.FloatType(), float(ctx.getText()))


    def visitParenthesis(self, ctx:CalcParser.ParenthesisContext):
        return self.visit(ctx.children[1])

    def promote(self, left, right):
        # TODO: Add difrent types and make this more generic
        if isinstance(left.type, ir.IntType) and isinstance(right.type, ir.FloatType): 
            left = self.builder.uitofp(left, ir.FloatType())
        elif isinstance(right.type, ir.IntType) and isinstance(left.type, ir.FloatType): 
            right = self.builder.uitofp(right, ir.FloatType())
        else:
            raise Exception("Wrong type to promote!")
        return left, right

    def visitBinary(self, ctx:CalcParser.BinaryContext):
        op = ctx.op.type
        left = self.visit(ctx.left)
        right = self.visit(ctx.right)

        if left.type != right.type:
            left, right = self.promote(left, right)

        if isinstance(left.type, ir.IntType): 
            if op == CalcLexer.PLUS:
                return self.builder.add(left, right)
            elif op == CalcLexer.MINUS:
                return self.builder.sub(left, right)
            elif op == CalcLexer.MULT:
                return self.builder.mul(left, right)
            elif op == CalcLexer.DIV:
                return self.builder.sdiv(left, right)

        elif isinstance(left.type, ir.FloatType): 
            if op == CalcLexer.PLUS:
                return self.builder.fadd(left, right)
            elif op == CalcLexer.MINUS:
                return self.builder.fsub(left, right)
            elif op == CalcLexer.MULT:
                return self.builder.fmul(left, right)
            elif op == CalcLexer.DIV:
                return self.builder.fdiv(left, right)

        else:
            raise Exception("Unsuported types in binary")

