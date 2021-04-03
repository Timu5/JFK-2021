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


        
    def visitArgs(self, ctx:CalcParser.ArgsContext):
        if ctx.children is None:
            return []
        args = []
        for arg in ctx.children:
            if not hasattr(arg, 'symbol'):
                args.append(self.visit(arg))
        return args

    def visitCall(self, ctx:CalcParser.BinaryContext):
        name = ctx.name.text
        args = self.visit(ctx.arguments)

        fn = self.module.get_global(name)
        # TODO: check if function and if fn exist

        if len(fn.args) != len(args):
            if not (fn.ftype.var_arg and len(fn.args) < len(args)):
                raise Exception("Wrong args number!")
        
        irargs = []
        for arg in args:
            arg_llvm = arg#.accept(self)
            if isinstance(arg_llvm.type, ir.PointerType):
                arg_llvm = self.builder.bitcast(arg_llvm, ir.IntType(8).as_pointer())
            elif fn.ftype.var_arg and isinstance(arg_llvm.type, ir.FloatType):
                arg_llvm = self.builder.fpext(arg_llvm, ir.DoubleType())

            irargs.append(arg_llvm)
        
        return self.builder.call(fn, irargs)

    def visitTenary(self, ctx:CalcParser.TenaryContext):
        # cond, truee, falsee
        cond = self.visit(ctx.cond)
        lhs = self.visit(ctx.truee)
        rhs = self.visit(ctx.falsee)

        if lhs.type != rhs.type:
            rhs, rhs = self.promote(lhs, rhs)

        if isinstance(cond.type, ir.IntType):
            cond = self.builder.icmp_signed("==", cond, ir.Constant(ir.IntType(32), 0))
        elif isinstance(cond.type, ir.FloatType):
            cond = self.builder.fcmp_ordered("==", cond, ir.Constant(ir.FloatType(), 0.0))
        #elif isinstance(cond.type, ir.PointerType):
        #    pass
        # TODO: check how to compare to NULL
        else:
            raise Exception("Unknown type for tenary cond!")
        
        return self.builder.select(cond, lhs, rhs)


    def visitBasicType(self, ctx:CalcParser.BasicTypeContext):
        name = ctx.getText()

        if name == "int":
            return ir.IntType(32)
        elif name == "byte":
            return ir.IntType(8)
        elif name == "short":
            return ir.IntType(16)
        elif name == "float":
            return ir.FloatType()
        
        raise Exception("Unknown type")

    def visitPointerType(self, ctx:CalcParser.PointerTypeContext):
        typ = self.visit(ctx.children[0])
        return typ.as_pointer()

    def visitArrayType(self, ctx:CalcParser.ArrayTypeContext):
        # TODO: Save somewhere info that this is array
        typ = self.visit(ctx.children[0])
        return typ.as_pointer()

    def visitFnargs(self, ctx:CalcParser.FnargsContext):
        args = []
        for arg in ctx.children:
            if not hasattr(arg, 'symbol'):
                args.append(self.visit(arg))
        return args

    def visitExtern(self, ctx:CalcParser.ExternContext):
        retval = self.visit(ctx.rettype)
        name = ctx.name.text
        args = self.visit(ctx.arguments)
        varargs = not ctx.varargs is None
        fn_ty = ir.FunctionType(retval, args, var_arg=varargs)
        ir.Function(self.module, fn_ty, name=name)