from llvmlite import ir
from antlr4 import *
from generated.CalcLexer import CalcLexer
from generated.CalcVisitor import CalcVisitor
from generated.CalcParser import CalcParser
import re


class CodegenException(Exception):
    def __init__(self, start, msg):
        self.line = start.line
        self.column = start.column
        self.msg = msg
        super().__init__(self.msg)


class Codegen(CalcVisitor):

    def __init__(self):
        self.builder = None
        self.module = None
        self.counter = 0
        self.locals = {}
        self.structs = {}

    def get_uniq(self):
        self.counter += 1
        return self.counter

    def gen_ir(self, node):
        self.module = ir.Module(name="my_super_modul")
        self.visit(node)
        return self.module

    def visitNumber(self, ctx: CalcParser.NumberContext):
        return ir.Constant(ir.IntType(32), int(ctx.getText()))

    def visitFloat(self, ctx: CalcParser.FloatContext):
        return ir.Constant(ir.FloatType(), float(ctx.getText()))

    def visitAddress(self, ctx: CalcParser.AddressContext):
        name = ctx.name.text
        return self.getVar(name, ctx)

    def visitDeref(self, ctx: CalcParser.DerefContext):
        name = ctx.name.text
        return self.builder.load(self.builder.load(self.getVar(name, ctx)))

    def visitString(self, ctx: CalcParser.StringContext):
        text = ctx.getText()[
            1:-1].encode('utf-8').decode('unicode_escape') + "\x00"
        text_const = ir.Constant(ir.ArrayType(ir.IntType(
            8), len(text)), bytearray(text.encode("utf8")))
        if self.builder is None:
            return text_const
        global_text = ir.GlobalVariable(
            self.module, text_const.type, name=".str."+str(self.get_uniq()))
        global_text.linkage = 'internal'
        global_text.global_constant = False
        global_text.initializer = text_const
        return global_text

    def visitArray(self, ctx: CalcParser.ArrayContext):
        args = self.visit(ctx.children[1])
        if len(args) == 0:
            raise CodegenException(ctx.start, "cannot create empty array")
        if any([not isinstance(a, ir.Constant) for a in args]):
            raise CodegenException(
                ctx.start, "array must be built from consts!")
        first_type = args[0].type
        if any([not a.type == first_type for a in args]):
            raise CodegenException(
                ctx.start, "array must be built from same types!")

        array_type = ir.ArrayType(first_type, len(args))
        array = ir.Constant(array_type, [x.constant for x in args])
        if self.builder is None:
            return array
        ptr = self.builder.alloca(array_type)
        self.builder.store(array, ptr)
        return ptr

    def visitIndex(self, ctx: CalcParser.IndexContext):
        primary = self.visit(ctx.children[0])
        expr = self.visit(ctx.children[2])

        if not isinstance(expr.type, ir.IntType):
            raise CodegenException(
                ctx.start, "array index need to be int type!")

        ptr = self.builder.gep(primary, [ir.Constant(ir.IntType(32), 0), expr])
        return self.builder.load(ptr)

    def visitMember(self, ctx: CalcParser.MemberContext):
        primary = self.visit(ctx.children[0])  # maybe dont pull whole object?
        name = ctx.children[2].getText()
        struct_name = primary.type.name
        struct = self.structs[struct_name]
        idx = next(i for i, v in enumerate(struct)
                   if (lambda x: x[0] == name)(v))
        # TODO: handle exception

        if isinstance(primary, ir.LoadInstr):
            primary = primary.operands[0]
            self.builder.block.instructions.pop()

        ptr = self.builder.gep(primary, [ir.Constant(
            ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)])
        return self.builder.load(ptr)

    def getVar(self, name, ctx):
        if name in self.locals:
            return self.locals[name]

        var = self.module.get_global(name)
        if not var is None:
            # TODO: check how this works with arrays and strings
            return var

        raise CodegenException(ctx.start, "unknown variable")

    def visitVar(self, ctx: CalcParser.VarContext):
        name = ctx.getText()
        var = self.getVar(name, ctx)

        if var.type.is_pointer:
            if isinstance(var.type.pointee, ir.ArrayType):
                return var

        return self.builder.load(var)

    def visitParenthesis(self, ctx: CalcParser.ParenthesisContext):
        return self.visit(ctx.children[1])

    def visitStructVal(self, ctx: CalcParser.StructValContext):
        name = ctx.name.text

        if not name in self.structs:
            raise CodegenException(ctx.start, "no struct with this name!")

        vtype = self.module.context.get_identified_type(name)

        args = self.visit(ctx.children[2])
        if len(args) == 0:
            raise CodegenException(ctx.start, "cannot create empty struct")
        if any([not isinstance(a, ir.Constant) for a in args]):
            raise CodegenException(
                ctx.start, "struct must be built from consts!")

        if any([not a.type == b for a, b in zip(args, vtype.elements)]):
            raise CodegenException(ctx.start, "types mismatch!")

        struct = ir.Constant(vtype, [x.constant for x in args])
        return struct

    def promote(self, left, right, ctx):
        # TODO: Add difrent types and make this more generic
        if isinstance(left.type, ir.IntType) and isinstance(right.type, ir.FloatType):
            left = self.builder.uitofp(left, ir.FloatType())
        elif isinstance(right.type, ir.IntType) and isinstance(left.type, ir.FloatType):
            right = self.builder.uitofp(right, ir.FloatType())
        else:
            raise CodegenException(ctx.start, "wrong type to promote!")
        return left, right

    def visitBinary(self, ctx: CalcParser.BinaryContext):
        op = ctx.op.type
        left = self.visit(ctx.left)
        right = self.visit(ctx.right)

        if left.type != right.type:
            left, right = self.promote(left, right, ctx)

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

        raise CodegenException(ctx.start, "unsuported types in binary")

    def visitCondBinary(self, ctx: CalcParser.CondBinaryContext):
        op = ctx.op.text
        left = self.visit(ctx.left)
        right = self.visit(ctx.right)

        if left.type != right.type:
            left, right = self.promote(left, right, ctx)

        if isinstance(left.type, ir.IntType):
            return self.builder.icmp_signed(op, left, right)
        elif isinstance(left.type, ir.FloatType):
            return self.builder.fcmp_ordered(op, left, right)

        raise CodegenException(ctx.start, "unusported type in compare")

    def visitArgs(self, ctx: CalcParser.ArgsContext):
        if ctx.children is None:
            return []
        args = []
        for arg in ctx.children:
            if not hasattr(arg, 'symbol'):
                args.append(self.visit(arg))
        return args

    def visitCall(self, ctx: CalcParser.BinaryContext):
        name = ctx.name.text
        args = self.visit(ctx.arguments)

        fn = self.module.get_global(name)
        # TODO: check if function and if fn exist

        if len(fn.args) != len(args):
            if not (fn.ftype.var_arg and len(fn.args) < len(args)):
                raise CodegenException(ctx.start, "Wrong args number!")

        irargs = []
        for arg in args:
            arg_llvm = arg  # .accept(self)
            if isinstance(arg_llvm.type, ir.PointerType):
                arg_llvm = self.builder.bitcast(
                    arg_llvm, ir.IntType(8).as_pointer())
            elif fn.ftype.var_arg and isinstance(arg_llvm.type, ir.FloatType):
                arg_llvm = self.builder.fpext(arg_llvm, ir.DoubleType())

            irargs.append(arg_llvm)

        return self.builder.call(fn, irargs)

    def visitTenary(self, ctx: CalcParser.TenaryContext):
        # cond, truee, falsee
        cond = self.visit(ctx.cond)
        lhs = self.visit(ctx.truee)
        rhs = self.visit(ctx.falsee)

        if lhs.type != rhs.type:
            rhs, rhs = self.promote(lhs, rhs, ctx)

        cond = self.convert_to_i1(cond, ctx)

        return self.builder.select(cond, lhs, rhs)

    def visitAssign(self, ctx: CalcParser.AssignContext):
        right = self.visit(ctx.right)

        left = self.visit(ctx.left)
        if isinstance(left, ir.LoadInstr):
            left = left.operands[0]
            self.builder.block.instructions.pop()

        if not left.type.is_pointer:
            raise CodegenException(
                ctx.start, "can only assign to variable, pointer, array element or struct member")

        self.builder.store(right, left)
        return right

    def convert_to_i1(self, value, ctx):
        if value.type == ir.IntType(1):
            return value
        if isinstance(value.type, ir.IntType):
            return self.builder.icmp_signed("!=", value, ir.Constant(ir.IntType(32), 0))
        elif isinstance(value.type, ir.FloatType):
            return self.builder.fcmp_ordered("!=", value, ir.Constant(ir.FloatType(), 0.0))
        # elif isinstance(cond.type, ir.PointerType):
        #    pass
        # TODO: check how to compare to NULL
        else:
            raise CodegenException(ctx.start, "unknown type for bool value!")

    def visitConditional(self, ctx: CalcParser.ConditionalContext):
        cond = self.visit(ctx.value)
        cond = self.convert_to_i1(cond, ctx)

        if ctx.falsee is None:
            with self.builder.if_then(cond) as then:
                self.visit(ctx.truee)
        else:
            with self.builder.if_else(cond) as (then, otherwise):
                with then:
                    self.visit(ctx.truee)
                with otherwise:
                    self.visit(ctx.falsee)

    def visitLoop(self, ctx: CalcParser.LoopContext):
        cond = self.visit(ctx.value)
        cond = self.convert_to_i1(cond, ctx)

        w_body_block = self.builder.append_basic_block("w_body")
        w_after_block = self.builder.append_basic_block("w_after")

        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_body_block)
        self.visit(ctx.block)

        cond = self.visit(ctx.value)
        cond = self.convert_to_i1(cond, ctx)
        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_after_block)

    def visitForLoop(self, ctx: CalcParser.ForLoopContext):
        cond = self.visit(ctx.b)
        cond = self.convert_to_i1(cond, ctx)

        self.visit(ctx.a)

        w_body_block = self.builder.append_basic_block("w_body")
        w_after_block = self.builder.append_basic_block("w_after")

        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_body_block)
        self.visit(ctx.block)
        self.visit(ctx.c)

        cond = self.visit(ctx.b)
        cond = self.convert_to_i1(cond, ctx)
        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_after_block)

    def visitBlock(self, ctx: CalcParser.BlockContext):
        statements = []
        for stm in ctx.children:
            if not hasattr(stm, 'symbol'):
                statements.append(self.visit(stm))
        return statements

    def visitDeclaration(self, ctx: CalcParser.DeclarationContext):
        if ctx.vartype is None and ctx.value is None:
            raise CodegenException(ctx.start, "variable need a type!")

        elif ctx.vartype is None and not ctx.value is None:
            value = self.visit(ctx.value)
            if value.type.is_pointer:
                self.locals[ctx.name.text] = value
                return
            ptr = self.builder.alloca(value.type)
            self.builder.store(value, ptr)
            self.locals[ctx.name.text] = ptr             

        elif not ctx.vartype is None and ctx.value is None:
            # only allocate space
            vartype = self.visit(ctx.vartype)
            ptr = self.builder.alloca(vartype)
            self.locals[ctx.name.text] = ptr

        else:
            raise CodegenException(ctx.start, "sorry not ready yet :/")

    def visitExpression(self, ctx: CalcParser.ExpressionContext):
        return self.visit(ctx.children[0])

    def visitReturn(self, ctx: CalcParser.ReturnContext):
        rtype = self.builder.function.ftype.return_type
        if ctx.value is None:
            if not isinstance(rtype, ir.VoidType):
                raise CodegenException(ctx.start, "return need to have value!")
            self.builder.ret_void()
        else:
            value = self.visit(ctx.value)
            if value.type != rtype:
                raise CodegenException(
                    ctx.start, "return need to have same type as function!")
            self.builder.ret(value)

    def visitGlobalVar(self, ctx: CalcParser.GlobalVarContext):
        value = self.visit(ctx.value)

        # TODO: add possibility to take global_variable
        if not isinstance(value, ir.Constant):
            raise CodegenException(ctx.start, "global vars need to be const!")

        # TODO: check global name redefinition!
        global_var = ir.GlobalVariable(
            self.module, value.type, name=ctx.name.text)
        global_var.global_constant = False
        global_var.initializer = value

        return global_var

    def visitBasicType(self, ctx: CalcParser.BasicTypeContext):
        name = ctx.getText()

        if name == "int":
            return ir.IntType(32)
        elif name == "byte":
            return ir.IntType(8)
        elif name == "short":
            return ir.IntType(16)
        elif name == "float":
            return ir.FloatType()
        elif name == "void":
            return ir.VoidType()
        elif name in self.structs:
            return self.module.context.get_identified_type(name)

        raise CodegenException(ctx.start, "unknown type")

    def visitPointerType(self, ctx: CalcParser.PointerTypeContext):
        typ = self.visit(ctx.children[0])
        return typ.as_pointer()

    def visitArrayType(self, ctx: CalcParser.ArrayTypeContext):
        typ = self.visit(ctx.children[0])
        if ctx.size == None:
            # TODO: Save somewhere info that this is array
            return typ.as_pointer()
        elements = int(ctx.size.text)
        return ir.ArrayType(typ, elements)

    def visitFnargs(self, ctx: CalcParser.FnargsContext):
        if ctx.children is None:
            return []
        args = []
        for arg in ctx.children:
            if not hasattr(arg, 'symbol'):
                args.append(self.visit(arg))
        return args

    def visitFnargsnamed(self, ctx: CalcParser.FnargsnamedContext):
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

    def visitFunction(self, ctx: CalcParser.FunctionContext):
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

        if len(self.builder.block.instructions) == 0 or not isinstance(self.builder.block.instructions[-1], ir.Ret):
            if isinstance(func.ftype.return_type, ir.VoidType):
                self.builder.ret_void()
            else:
                raise CodegenException(ctx.start, "missing return")

        self.locals = None
        self.builder = None

    def visitExternVar(self, ctx: CalcParser.ExternVarContext):
        name = ctx.name.text
        vartype = self.visit(ctx.vartype)
        global_text = ir.GlobalVariable(self.module, vartype, name=name)
        global_text.linkage = 'external'
        global_text.global_constant = False
        return global_text

    def visitExtern(self, ctx: CalcParser.ExternContext):
        retval = self.visit(ctx.rettype)
        name = ctx.name.text
        args = self.visit(ctx.arguments)
        varargs = not ctx.varargs is None
        fn_ty = ir.FunctionType(retval, args, var_arg=varargs)
        ir.Function(self.module, fn_ty, name=name)

    def visitStructMember(self, ctx: CalcParser.StructMemberContext):
        vtype = self.visit(ctx.membertype)
        name = ctx.name.text
        return name, vtype

    def visitStructMembers(self, ctx: CalcParser.StructMembersContext):
        if ctx.children is None:
            return []
        members = []
        for member in ctx.children:
            if not hasattr(member, 'symbol'):
                members.append(self.visit(member))
        return members

    def visitStruct(self, ctx: CalcParser.StructContext):
        name = ctx.name.text
        members = self.visit(ctx.members)

        if name in self.structs:
            raise CodegenException(ctx.start, "struct redefinition!")

        self.structs[name] = members
        b = self.module.context.get_identified_type(name)
        b.set_body(*[x[1] for x in members])
