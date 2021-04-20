from llvmlite import ir
from antlr4 import *
from generated.LangLexer import LangLexer
from generated.LangVisitor import LangVisitor
from generated.LangParser import LangParser
from Utils import *


class Codegen(LangVisitor):

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

    def visitNumber(self, ctx: LangParser.NumberContext):
        valtype = SignedType(32, True)
        if not ctx.literal is None:
            if ctx.literal.text == 'u':
                valtype = SignedType(32, False)
            elif ctx.literal.text == 'i':
                valtype = SignedType(32, True)
            elif ctx.literal.text == 'ul':
                valtype = SignedType(64, False)
            elif ctx.literal.text == 'l':
                valtype = SignedType(64, True)
            elif ctx.literal.text == 'us':
                valtype = SignedType(16, False)
            elif ctx.literal.text == 's':
                valtype = SignedType(16, True)
            elif ctx.literal.text == 'ub':
                valtype = SignedType(8, False)
            elif ctx.literal.text == 'b':
                valtype = SignedType(8, True)
            else:
                raise CodegenException(ctx.start, "unkdown interger literal")
        return ir.Constant(valtype, int(ctx.value.text))

    def visitFloat(self, ctx: LangParser.FloatContext):
        valtype = ir.DoubleType()
        if not ctx.literal is None:
            if ctx.literal.text == 'h':
                valtype = ir.HalfType()
            elif ctx.literal.text == 'f':
                valtype = ir.FloatType()
            elif ctx.literal.text == 'd':
                valtype = ir.DoubleType()
            else:
                raise CodegenException(ctx.start, "unkdown float literal")
        return ir.Constant(valtype, float(ctx.value.text))

    def visitAddress(self, ctx: LangParser.AddressContext):
        value = self.visit(ctx.value)

        if isinstance(value, ir.LoadInstr):
            value = value.operands[0]
            self.builder.block.instructions.pop()
        elif isinstance(value, ir.GlobalVariable):
            pass
        else:
            raise CodegenException(ctx.start, "cannot obtain value of this element")

        return value

    def visitDeref(self, ctx: LangParser.DerefContext):
        value = self.visit(ctx.value)
        if not isinstance(value.type, ir.PointerType):
            raise CodegenException(ctx.start, "can only derefernece pointers")
        return self.builder.load(value)

    def visitString(self, ctx: LangParser.StringContext):
        text = ctx.getText()[
            1:-1].encode('utf-8').decode('unicode_escape') + "\x00"
        text_const = ir.Constant(ir.ArrayType(SignedType(
            8, False), len(text)), bytearray(text.encode("utf8")))
        if self.builder is None:
            return text_const
        global_text = ir.GlobalVariable(
            self.module, text_const.type, name=".str."+str(self.get_uniq()))
        global_text.linkage = 'internal'
        global_text.global_constant = False
        global_text.initializer = text_const
        return global_text

    def visitArray(self, ctx: LangParser.ArrayContext):
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

    def visitChar(self, ctx: LangParser.CharContext):
        value = ord(ctx.getText()[1:-1])
        return ir.Constant(SignedType(8, False), value)

    def visitCast(self, ctx: LangParser.CastContext):
        vartype = self.visit(ctx.vartype)
        value = self.visit(ctx.value)

        if vartype == value.type:
            print("warning: casting to some type")

        if isinstance(value.type, ir.IntType) and isinstance(vartype, ir.types._BaseFloatType):
            # TODO: singed vs unsigned
            value = self.builder.uitofp(value, vartype)
        elif isinstance(vartype, ir.IntType) and isinstance(value.type, ir.types._BaseFloatType):
            # TODO: singed vs unsigned
            value = self.builder.fptoui(value, vartype)
        elif isinstance(value.type, ir.IntType) and isinstance(vartype, ir.IntType):
            if value.type.width > vartype.width:
                value = self.builder.trunc(value, vartype)
            elif value.type.width < vartype.width:
                # TODO: singed vs unsigned
                value = self.builder.sext(value, vartype)
        elif isinstance(value.type, ir.PointerType) and isinstance(vartype, ir.PointerType):
            value = self.builder.bitcast(value, vartype)
        else:
            raise CodegenException(ctx.start, "wrong type to cast!")

        return value

    def visitIndex(self, ctx: LangParser.IndexContext):
        primary = self.visit(ctx.children[0])
        expr = self.visit(ctx.children[2])

        if not isinstance(expr.type, ir.IntType):
            raise CodegenException(
                ctx.start, "array index need to be int type!")

        ptr = self.builder.gep(primary, [ir.Constant(SignedType(32, True), 0), expr])
        return self.builder.load(ptr)

    def visitUnary(self, ctx:LangParser.UnaryContext):
        op = ctx.op
        primary = self.visit(ctx.primary)

        if op == LangLexer.NOT:
            primary = self.convert_to_i1(ctx, primary)
            primary = self.builder.not_(primary)

        elif op == LangLexer.PLUS or op == LangLexer.MINUS:
            if not isNumber(primary):
                raise CodegenException(ctx.start, "cannot perform unary plus and minus on non numbers")
            if op == LangLexer.MINUS:
                if isinstance(primary.type, ir.IntType):
                    primary = self.builder.neg(primary)
            else:
                pass
        
        return primary


    def visitMember(self, ctx: LangParser.MemberContext):
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
            SignedType(32, True), 0), ir.Constant(SignedType(32, True), idx)])
        return self.builder.load(ptr)

    def getVar(self, name, ctx):
        if name in self.locals:
            return self.locals[name]

        var = self.module.get_global(name)
        if not var is None:
            # TODO: check how this works with arrays and strings
            return var

        raise CodegenException(ctx.start, "unknown variable")

    def visitVar(self, ctx: LangParser.VarContext):
        name = ctx.getText()
        var = self.getVar(name, ctx)

        if var.type.is_pointer:
            if isinstance(var.type.pointee, ir.ArrayType):
                return var

        return self.builder.load(var)

    def visitParenthesis(self, ctx: LangParser.ParenthesisContext):
        return self.visit(ctx.children[1])

    def visitStructVal(self, ctx: LangParser.StructValContext):
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

    def visitAndOr(self, ctx:LangParser.AndOrContext):
        op = ctx.op.text
        left = self.visit(ctx.left)
        right = self.visit(ctx.right)
        left = self.convert_to_i1(left, ctx.left)
        right = self.convert_to_i1(right, ctx.right)

        if op == 'or':
            return self.builder.or_(left, right)
        elif op == 'and':
            return self.builder.and_(left, right)

        raise CodegenException(ctx.start, "unknown operator") 

    def promote(self, left, right, ctx):
        # TODO: Add difrent types and make this more generic
        if isinstance(left.type, ir.IntType) and isinstance(right.type, ir.FloatType):
            left = self.builder.uitofp(left, ir.FloatType())
        elif isinstance(right.type, ir.IntType) and isinstance(left.type, ir.FloatType):
            right = self.builder.uitofp(right, ir.FloatType())
        else:
            raise CodegenException(ctx.start, "wrong type to promote!")
        return left, right

    def visitBinary(self, ctx: LangParser.BinaryContext):
        op = ctx.op.type
        left = self.visit(ctx.left)
        right = self.visit(ctx.right)

        if left.type != right.type:
            left, right = self.promote(left, right, ctx)

        if isinstance(left.type, ir.IntType):
            if op == LangLexer.PLUS:
                return self.builder.add(left, right)
            elif op == LangLexer.MINUS:
                return self.builder.sub(left, right)
            elif op == LangLexer.MULT:
                return self.builder.mul(left, right)
            elif op == LangLexer.DIV:
                if left.type.is_signed and right.type.is_signed:
                    return self.builder.sdiv(left, right)
                elif left.type.is_unsigned and right.type.is_unsigned:
                    return self.builder.udiv(left, right)
                else:
                    raise CodegenException(ctx.op.start, "mix between signed and unsigned values")

        elif isinstance(left.type, ir.FloatType):
            if op == LangLexer.PLUS:
                return self.builder.fadd(left, right)
            elif op == LangLexer.MINUS:
                return self.builder.fsub(left, right)
            elif op == LangLexer.MULT:
                return self.builder.fmul(left, right)
            elif op == LangLexer.DIV:
                return self.builder.fdiv(left, right)

        raise CodegenException(ctx.start, "unsuported types in binary")

    def visitCondBinary(self, ctx: LangParser.CondBinaryContext):
        op = ctx.op.text
        left = self.visit(ctx.left)
        right = self.visit(ctx.right)

        if left.type != right.type:
            left, right = self.promote(left, right, ctx)

        if isinstance(left.type, ir.IntType):
            if left.type.is_signed and right.type.is_signed:
                return self.builder.icmp_signed(op, left, right)
            elif left.type.is_unsigned and right.type.is_unsigned:
                return self.builder.icmp_unsigned(op, left, right)
            else:
                raise CodegenException(ctx.op.start, "mix between signed and unsigned values")
            
        elif isinstance(left.type, ir.FloatType):
            return self.builder.fcmp_ordered(op, left, right)

        raise CodegenException(ctx.start, "unusported type in compare")

    def visitArgs(self, ctx: LangParser.ArgsContext):
        if ctx.children is None:
            return []
        args = []
        for arg in ctx.children:
            if not hasattr(arg, 'symbol'):
                args.append(self.visit(arg))
        return args

    def visitCall(self, ctx: LangParser.BinaryContext):
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
                    arg_llvm, SignedType(8, False).as_pointer())
            elif fn.ftype.var_arg and isinstance(arg_llvm.type, ir.FloatType):
                arg_llvm = self.builder.fpext(arg_llvm, ir.DoubleType())

            irargs.append(arg_llvm)

        return self.builder.call(fn, irargs)

    def visitTenary(self, ctx: LangParser.TenaryContext):
        # cond, truee, falsee
        cond = self.visit(ctx.cond)
        lhs = self.visit(ctx.truee)
        rhs = self.visit(ctx.falsee)

        if lhs.type != rhs.type:
            rhs, rhs = self.promote(lhs, rhs, ctx)

        cond = self.convert_to_i1(cond, ctx)

        return self.builder.select(cond, lhs, rhs)

    def visitAssign(self, ctx: LangParser.AssignContext):
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
            return self.builder.icmp_signed("!=", value, ir.Constant(value.type, 0))
        elif isinstance(value.type, ir.FloatType) or isinstance(value.type, ir.HalfType) or isinstance(value.type, ir.DoubleType):
            return self.builder.fcmp_ordered("!=", value, ir.Constant(value.type, 0.0))
        # elif isinstance(cond.type, ir.PointerType):
        #    pass
        # TODO: check how to compare to NULL
        else:
            raise CodegenException(ctx.start, "unknown type for bool value!")

    def visitConditional(self, ctx: LangParser.ConditionalContext):
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

    def visitLoop(self, ctx: LangParser.LoopContext):
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

    def visitForLoop(self, ctx: LangParser.ForLoopContext):
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

    '''def visitBlock(self, ctx: LangParser.BlockContext):
        statements = []
        for stm in ctx.children:
            if not hasattr(stm, 'symbol'):
                statements.append(self.visit(stm))
        return statements'''

    def visitDeclaration(self, ctx: LangParser.DeclarationContext):
        if ctx.name.text in self.locals:
            raise CodegenException(ctx.start, "variable redefinition!")
        
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

    def visitExpression(self, ctx: LangParser.ExpressionContext):
        return self.visit(ctx.children[0])

    def visitReturn(self, ctx: LangParser.ReturnContext):
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

    def visitGlobalVar(self, ctx: LangParser.GlobalVarContext):
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

    def visitBasicType(self, ctx: LangParser.BasicTypeContext):
        name = ctx.getText()

        if name == "int":
            return SignedType(32, True)
        elif name == "uint":
            return SignedType(32, False)
        elif name == "byte":
            return SignedType(8, True)
        elif name == "ubyte":
            return SignedType(8, False)
        elif name == "short":
            return SignedType(16, True)
        elif name == "ushort":
            return SignedType(16, False)
        elif name == "long":
            return SignedType(64, True)
        elif name == "ulong":
            return SignedType(64, False)
        elif name == "half":
            return ir.HalfType()
        elif name == "float":
            return ir.FloatType()
        elif name == "double":
            return ir.DoubleType()
        elif name == "void":
            return ir.VoidType()
        elif name in self.structs:
            return self.module.context.get_identified_type(name)

        raise CodegenException(ctx.start, "unknown type")

    def visitPointerType(self, ctx: LangParser.PointerTypeContext):
        typ = self.visit(ctx.children[0])
        return typ.as_pointer()

    def visitArrayType(self, ctx: LangParser.ArrayTypeContext):
        typ = self.visit(ctx.children[0])
        if ctx.size == None:
            # TODO: Save somewhere info that this is array
            return typ.as_pointer()
        elements = int(ctx.size.text)
        return ir.ArrayType(typ, elements)

    def visitFnargs(self, ctx: LangParser.FnargsContext):
        if ctx.children is None:
            return []
        args = []
        for arg in ctx.children:
            if not hasattr(arg, 'symbol'):
                args.append(self.visit(arg))
        return args

    def visitFnargsnamed(self, ctx: LangParser.FnargsnamedContext):
        if ctx.children is None:
            return [], []
        args = []
        args_names = []
        for i, arg in enumerate(ctx.children):
            if i % 4 == 0:
                args_names.append(arg.getText())
            if i % 4 == 2:
                args.append(self.visit(arg))
        return args, args_names

    def visitFunction(self, ctx: LangParser.FunctionContext):
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

    def visitExternVar(self, ctx: LangParser.ExternVarContext):
        name = ctx.name.text
        vartype = self.visit(ctx.vartype)
        global_text = ir.GlobalVariable(self.module, vartype, name=name)
        global_text.linkage = 'external'
        global_text.global_constant = False
        return global_text

    def visitExtern(self, ctx: LangParser.ExternContext):
        retval = self.visit(ctx.rettype)
        name = ctx.name.text
        args = self.visit(ctx.arguments)
        varargs = not ctx.varargs is None
        fn_ty = ir.FunctionType(retval, args, var_arg=varargs)
        ir.Function(self.module, fn_ty, name=name)

    def visitStructMember(self, ctx: LangParser.StructMemberContext):
        vtype = self.visit(ctx.membertype)
        name = ctx.name.text
        return name, vtype

    def visitStructMembers(self, ctx: LangParser.StructMembersContext):
        if ctx.children is None:
            return []
        members = []
        for member in ctx.children:
            if not hasattr(member, 'symbol'):
                members.append(self.visit(member))
        return members

    def visitStruct(self, ctx: LangParser.StructContext):
        name = ctx.name.text
        members = self.visit(ctx.members)

        if name in self.structs:
            raise CodegenException(ctx.start, "struct redefinition!")

        self.structs[name] = members
        b = self.module.context.get_identified_type(name)
        b.set_body(*[x[1] for x in members])
