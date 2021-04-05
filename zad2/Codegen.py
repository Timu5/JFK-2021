from llvmlite import ir
from antlr4 import *
from generated.CalcLexer import CalcLexer
from generated.CalcVisitor import CalcVisitor
from generated.CalcParser import CalcParser
import re

class Codegen(CalcVisitor):

    def __init__(self):
        self.builder = None
        self.module = None
        #self.printf = None
        self.counter = 0
        self.locals = {}

    def get_uniq(self):
        self.counter += 1
        return self.counter

    def gen_ir(self, node):
        # Create an empty module...
        self.module = ir.Module(name="my_super_modul")

        #printf_ty = ir.FunctionType(ir.IntType(32), [ir.IntType(8).as_pointer()], var_arg=True)
        #self.printf = ir.Function(self.module, printf_ty, name="printf")

        #fnty = ir.FunctionType(ir.VoidType(), [])
        #func = ir.Function(self.module, fnty, name="start")

        # Now implement the function
        #block = func.append_basic_block(name="entry")
        #self.builder = ir.IRBuilder(block)

        self.visit(node)
        #self.builder.ret_void()

        return self.module

    def visitNumber(self, ctx:CalcParser.NumberContext):
        return ir.Constant(ir.IntType(32), int(ctx.getText()))

    def visitFloat(self, ctx:CalcParser.FloatContext):
        return ir.Constant(ir.FloatType(), float(ctx.getText()))

    def visitAddress(self, ctx:CalcParser.AddressContext):
        name = ctx.name.text
        return self.getVar(name)

    def visitDeref(self, ctx:CalcParser.DerefContext):
        name = ctx.name.text
        return self.builder.load(self.builder.load(self.getVar(name)))

    def visitString(self, ctx:CalcParser.StringContext):
        text = ctx.getText()[1:-1].encode('utf-8').decode('unicode_escape') + "\x00"
        text_const = ir.Constant(ir.ArrayType(ir.IntType(8), len(text)), bytearray(text.encode("utf8")))
        global_text = ir.GlobalVariable(self.module, text_const.type, name=".str."+str(self.get_uniq()))
        global_text.linkage = 'internal'
        global_text.global_constant = False
        global_text.initializer = text_const
        return global_text

    def visitArray(self, ctx:CalcParser.ArrayContext):
        args = self.visit(ctx.children[1])
        if len(args) == 0:
            raise Exception("Cannot create empty array")
        if any([not isinstance(a, ir.Constant) for a in args]):
            raise Exception("Array must be built from consts!")
        first_type = args[0].type
        if any([not a.type == first_type for a in args]):
            raise Exception("Array must be built from same types!")

        array_type = ir.ArrayType(first_type, len(args))
        array = ir.Constant(array_type, [x.constant for x in args])
        ptr = self.builder.alloca(array_type)
        self.builder.store(array, ptr)
        
        return ptr

    def visitIndex(self, ctx:CalcParser.IndexContext):
        primary = self.visit(ctx.children[0])
        expr = self.visit(ctx.children[2])

        if not isinstance(expr.type, ir.IntType):
            raise Exception("Array index need to be int type!")

        ptr = self.builder.gep(primary, [ir.Constant(ir.IntType(32), 0), expr])

        return self.builder.load(ptr)

    
    def getVar(self, name):
        if name in self.locals:
            return self.locals[name]

        var = self.module.get_global(name)
        if not var is None:
            # TODO: check how this works with arrays and strings
            return var

        raise Exception("Unknown variable")

    
    def visitVar(self, ctx:CalcParser.VarContext):
        name = ctx.getText() 
        '''if name in self.locals:
            return self.builder.load(self.locals[name])

        var = self.module.get_global(name)
        if not var is None:
            # TODO: check how this works with arrays and strings
            return self.builder.load(var)'''

        var = self.getVar(name)

        if isinstance(var, ir.GlobalVariable):
            if isinstance(var.value_type, ir.ArrayType):
                return var

        return self.builder.load(var)
        

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


    def visitCondBinary(self, ctx:CalcParser.CondBinaryContext):
        op = ctx.op.text
        left = self.visit(ctx.left)
        right = self.visit(ctx.right)

        if left.type != right.type:
            left, right = self.promote(left, right)

        if isinstance(left.type, ir.IntType): 
            return self.builder.icmp_signed(op, left, right)
        elif isinstance(left.type, ir.FloatType):
            return self.builder.fcmp_ordered(op, left, right)

        raise Exception("Unusported type in compare")

        
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

    def visitAssign(self, ctx:CalcParser.AssignContext):
        right = self.visit(ctx.right)

        if isinstance(ctx.left.children[0], CalcParser.VarContext):
            name = ctx.left.getText()
            if name in self.locals:        
                self.builder.store(right, self.locals[name])
                return right

            raise Exception("Undefined variable")

        raise Exception("Cannot assign to anything difrent than varaible")        


    def convert_to_i1(self, value):
        if value.type == ir.IntType(1):
            return value
        if isinstance(value.type, ir.IntType):
            return self.builder.icmp_signed("!=", value, ir.Constant(ir.IntType(32), 0))
        elif isinstance(value.type, ir.FloatType):
            return self.builder.fcmp_ordered("!=", value, ir.Constant(ir.FloatType(), 0.0))
        #elif isinstance(cond.type, ir.PointerType):
        #    pass
        # TODO: check how to compare to NULL
        else:
            raise Exception("Unknown type for bool value!")

    def visitConditional(self, ctx:CalcParser.ConditionalContext):
        cond = self.visit(ctx.value)
        cond = self.convert_to_i1(cond)

        if ctx.falsee is None:
            with self.builder.if_then(cond) as then:
                self.visit(ctx.truee)
        else:
            with self.builder.if_else(cond) as (then, otherwise):
                with then:
                    self.visit(ctx.truee)
                with otherwise:
                    self.visit(ctx.falsee)

    def visitLoop(self, ctx:CalcParser.LoopContext):
        cond = self.visit(ctx.value)
        cond = self.convert_to_i1(cond)

        w_body_block = self.builder.append_basic_block("w_body")
        w_after_block = self.builder.append_basic_block("w_after")

        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_body_block)
        self.visit(ctx.block)

        cond = self.visit(ctx.value)
        cond = self.convert_to_i1(cond)
        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_after_block)


    def visitForLoop(self, ctx:CalcParser.ForLoopContext):
        cond = self.visit(ctx.b)
        cond = self.convert_to_i1(cond)

        self.visit(ctx.a)

        w_body_block = self.builder.append_basic_block("w_body")
        w_after_block = self.builder.append_basic_block("w_after")

        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_body_block)
        self.visit(ctx.block)
        self.visit(ctx.c)

        cond = self.visit(ctx.b)
        cond = self.convert_to_i1(cond)
        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_after_block)

    def visitBlock(self, ctx:CalcParser.BlockContext):
        statements = []
        for stm in ctx.children:
            if not hasattr(stm, 'symbol'):
                statements.append(self.visit(stm))
        return statements

    def visitDeclaration(self, ctx:CalcParser.DeclarationContext):
        value = self.visit(ctx.value)        
        
        ptr = self.builder.alloca(value.type)
        self.locals[ctx.name.text] = ptr

        self.builder.store(value, ptr)

    def visitExpression(self, ctx:CalcParser.ExpressionContext):
        return self.visit(ctx.children[0])

    def visitReturn(self, ctx:CalcParser.ReturnContext):
        if ctx.value is None:
            self.builder.ret_void()
        else:
            self.builder.ret(self.visit(ctx.value))

    def visitGlobalVar(self, ctx:CalcParser.GlobalVarContext):
        value = self.visit(ctx.value)

        # TODO: add possibility to take global_variable
        if not isinstance(value, ir.Constant):
            raise Exception("Global vars need to be const!")

        # TODO: check global name redefinition!
        global_var = ir.GlobalVariable(self.module, value.type, name=ctx.name.text)
        global_var.global_constant = False
        global_var.initializer = value

        return global_var

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
        if ctx.children is None:
            return []
        args = []
        for arg in ctx.children:
            if not hasattr(arg, 'symbol'):
                args.append(self.visit(arg))
        return args

    def visitFnargsnamed(self, ctx:CalcParser.FnargsnamedContext):
        if ctx.children is None:
            return [], []
        args = []
        args_names = []
        for i, arg in enumerate(ctx.children):
            if i % 3 == 0:
                args.append(self.visit(arg))
            if i % 3 == 1:
                args_names.append(arg.getText())
        return args, args_names

    def visitFunction(self, ctx:CalcParser.FunctionContext):
        retval = self.visit(ctx.rettype)
        name = ctx.name.text
        args, args_names = self.visit(ctx.arguments)
        varargs = not ctx.varargs is None
        fn_ty = ir.FunctionType(retval, args, var_arg=varargs)
        func = ir.Function(self.module, fn_ty, name=name)

        block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

        self.locals = {}

        for index, value in enumerate(func.args):
            atype = args[index]
            aname = args_names[index]
            ptr = self.builder.alloca(atype)
            self.locals[aname] = ptr
            self.builder.store(value, ptr)     

        self.visit(ctx.block)

        # TODO: detect missing return!

        self.locals = None
        self.builder = None

    def visitExtern(self, ctx:CalcParser.ExternContext):
        retval = self.visit(ctx.rettype)
        name = ctx.name.text
        args = self.visit(ctx.arguments)
        varargs = not ctx.varargs is None
        fn_ty = ir.FunctionType(retval, args, var_arg=varargs)
        ir.Function(self.module, fn_ty, name=name)