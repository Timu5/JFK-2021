from llvmlite import ir
import llvmlite.binding as llvm
from antlr4 import *
from generated.LangLexer import LangLexer
from generated.LangParserVisitor import LangParserVisitor
from generated.LangParser import LangParser
from Utils import *
from Runtime import *

class Codegen(LangParserVisitor):

    def __init__(self, driver, target_machine):
        self.driver = driver
        self.target_machine = target_machine
        self.builder = None
        self.module = None
        self.runtime = None
        self.counter = 0
        self.locals = {}
        self.structs = {}
        self.templates = {}
        self.loops = []
        self.types = {}

    def get_uniq(self):
        self.counter += 1
        return self.counter

    def gen_ir(self, node):
        self.module = ir.Module(name="my_super_modul", context=ir.Context())
        self.module.triple = self.target_machine.triple
        self.module.data_layout = str(self.target_machine.target_data)
        self.runtime = get_runtime_functions(self.module)
        self.visit(node)
        self.module.templates = self.templates
        self.module.structs = self.structs
        return self.module

    def visitNumber(self, ctx: LangParser.NumberContext):
        valtype = int_
        if not ctx.literal is None:
            if ctx.literal.text == 'u':
                valtype = uint
            elif ctx.literal.text == 'i':
                valtype = int_
            elif ctx.literal.text == 'ul':
                valtype = ulong
            elif ctx.literal.text == 'l':
                valtype = long_
            elif ctx.literal.text == 'us':
                valtype = ushort
            elif ctx.literal.text == 's':
                valtype = short_
            elif ctx.literal.text == 'ub':
                valtype = ubyte
            elif ctx.literal.text == 'b':
                valtype = byte_
            else:
                raise CodegenException(ctx.start, f"unknown interger literal '{ctx.literal.text}'")
        return ir.Constant(valtype, int(ctx.value.text))

    def visitFloat(self, ctx: LangParser.FloatContext):
        valtype = double_
        if not ctx.literal is None:
            if ctx.literal.text == 'h':
                valtype = half_
            elif ctx.literal.text == 'f':
                valtype = float_
            elif ctx.literal.text == 'd':
                valtype = double_
            else:
                raise CodegenException(ctx.start, f"unknown float literal '{ctx.literal.text}'")
        return ir.Constant(valtype, float(ctx.value.text))

    def visitAddress(self, ctx: LangParser.AddressContext):
        value = self.visit(ctx.value)

        if isinstance(value, ir.LoadInstr):
            value = value.operands[0]
            self.builder.block.instructions.pop()
        elif isinstance(value, ir.GlobalVariable):
            pass
        else:
            raise CodegenException(
                ctx.start, "cannot obtain address of this element")

        return value

    def visitDeref(self, ctx: LangParser.DerefContext):
        value = self.visit(ctx.value)
        if not isinstance(value.type, ir.PointerType):
            raise CodegenException(ctx.start, f"can only derefernece pointers not {type2str(value.type)}")
        return self.builder.load(value)

    def visitFstring(self, ctx: LangParser.FstringContext):
        if len(ctx.children) <= 2:
            # empty string
            return [self.createString("")]
        elements = []
        for child in ctx.children[1:-1]:
            el = self.visit(child)
            elements.append(el)
        
        return elements

    def createString(self, text):
        text += '\x00'
        text_type = ir.ArrayType(ubyte, len(text))
        text_const = ir.Constant(text_type, bytearray(text.encode("utf8")))

        if self.builder is None:
            global_arr = ir.GlobalVariable(self.module, text_type, name=".str."+str(self.get_uniq()))
            global_arr.linkage = 'internal'
            global_arr.global_constant = False
            global_arr.initializer = text_const

            global_gep = global_arr.gep([int_(0), int_(0)])
            global_bit = global_gep.bitcast(ir.ArrayType(text_type.element, 1).as_pointer())

            return ir.Constant(StringType(), [ulong(len(text)-1), global_bit])

        ptr = self.builder.alloca(text_type)
        self.builder.store(text_const, ptr)

        new_array_type = StringType()
        newptr = self.builder.alloca(new_array_type)
        
        ptr = self.builder.gep(ptr, [int_(0), int_(0)])
        ptr = self.builder.bitcast(ptr, ir.ArrayType(text_type.element, 1).as_pointer())
        
        ptr_size = self.builder.gep(newptr, [int_(0), int_(0)])
        ptr_ptr = self.builder.gep(newptr, [int_(0), int_(1)])
        
        self.builder.store(ulong(len(text)-1), ptr_size)
        self.builder.store(ptr, ptr_ptr)

        return self.builder.load(newptr)

    def visitRawString(self, ctx:LangParser.RawStringContext):
        text = text = ctx.getText().encode('utf-8').decode('unicode_escape');
        return self.createString(text)

    def visitExprString(self, ctx:LangParser.ExprStringContext):
        value = self.visit(ctx.value)
        return self.toStr(ctx, value)

    def visitString(self, ctx: LangParser.StringContext):
        elements = self.visit(ctx.children[0])

        while len(elements) > 1:
            left = elements.pop(0)
            right = elements.pop(0)
            c = self.builder.call(self.runtime['string_add'], [left, right, self.runtime['GC_malloc_atomic']])
            elements.insert(0, c)

        return elements[0]

    def visitArray(self, ctx: LangParser.ArrayContext):
        args = self.visit(ctx.children[1])
        const = True
        if len(args) == 0:
            raise CodegenException(ctx.start, "cannot create empty array")
        if any([not isinstance(a, ir.Constant) for a in args]):
            const = False
            if self.builder is None:
                raise CodegenException(
                    ctx.start, "array must be built from consts elements")
        first_type = args[0].type
        if any([not a.type == first_type for a in args]):
            raise CodegenException(
                ctx.start, "array must be built from same types")

        array_type = ir.ArrayType(first_type, len(args))

        array = ir.Constant(array_type, [ir.Constant(first_type, 0) for x in args])
        if const:
            array = ir.Constant(array_type, [x.constant for x in args])
        if self.builder is None:
            # global array
            global_arr = ir.GlobalVariable(self.module, array_type, name=".arr."+str(self.get_uniq()))
            global_arr.linkage = 'internal'
            global_arr.global_constant = False
            global_arr.initializer = array

            global_gep = global_arr.gep([int_(0), int_(0)])
            global_bit = global_gep.bitcast(ir.ArrayType(args[0].type, 1).as_pointer())

            return ir.Constant(SizedArrayType(first_type), [ulong(len(args)), global_bit])
        
        ptr = self.builder.alloca(array_type)

        if not const:
            for i, x in enumerate(args):
                el_ptr = self.builder.gep(ptr, [int_(0), int_(i)])
                self.builder.store(x, el_ptr)
        else:
            self.builder.store(array, ptr)

        new_array_type = SizedArrayType(args[0].type)
        newptr = self.builder.alloca(new_array_type)
        
        ptr = self.builder.gep(ptr, [int_(0), int_(0)])
        ptr = self.builder.bitcast(ptr, ir.ArrayType(args[0].type, 1).as_pointer())
        
        ptr_size = self.builder.gep(newptr, [int_(0), int_(0)])
        ptr_ptr = self.builder.gep(newptr, [int_(0), int_(1)])
        
        self.builder.store(ulong(len(args)), ptr_size)
        self.builder.store(ptr, ptr_ptr)

        return self.builder.load(newptr)

    def visitChar(self, ctx: LangParser.CharContext):
        text = ctx.getText()[1:-1]
        if len(text) > 1:
            text = text.encode('utf-8').decode('unicode_escape')
        value = ord(text)
        return ubyte(value)

    def cast(self, value, vartype):
        if isinstance(value.type, ir.IntType) and isinstance(vartype, ir.types._BaseFloatType):
            if isSigned(value):
                value = self.builder.sitofp(value, vartype)
            else:
                value = self.builder.uitofp(value, vartype)
        elif isinstance(vartype, ir.IntType) and isinstance(value.type, ir.types._BaseFloatType):
            if isSigned(value):
                value = self.builder.fptosi(value, vartype)
            else:
                value = self.builder.fptoui(value, vartype)
        elif isinstance(value.type, ir.IntType) and isinstance(vartype, ir.IntType):
            if value.type.width > vartype.width:
                value = self.builder.trunc(value, vartype)
            else:
                if isSigned(value):
                    value = self.builder.sext(value, vartype)
                else:
                    value = self.builder.zext(value, vartype)
        elif isinstance(value.type, ir.types._BaseFloatType) and isinstance(vartype, ir.types._BaseFloatType):
            sizeleft = int(value.type.intrinsic_name[1:])
            sizeright = int(vartype.intrinsic_name[1:])
            if sizeright > sizeleft:
                value = self.builder.fpext(value, vartype)
            else:
                value = self.builder.fptrunc(value, vartype)
        elif isinstance(value.type, ir.PointerType) and isinstance(vartype, ir.PointerType):
            value = self.builder.bitcast(value, vartype)
        else:
            return None

        value.type = vartype

        return value


    def visitCast(self, ctx: LangParser.CastContext):
        vartype = self.visit(ctx.vartype)
        value = self.visit(ctx.value)
        oldtype = value.type

        if vartype == value.type:
            print("warning: casting to same type")

        value = self.cast(value, vartype)
        if value is None:
            raise CodegenException(ctx.start, f"cannot cast from {type2str(oldtype)} to {type2str(vartype)}")

        return value

    def visitIndex(self, ctx: LangParser.IndexContext):
        primary = self.visit(ctx.children[0])

        if not isinstance(primary.type, SizedArrayType) and not isinstance(primary.type, StringType):
            raise CodegenException(
                ctx.start, "not a proper array to access")
        
        if not isinstance(primary, ir.LoadInstr):
            raise CodegenException(ctx.start, "hle?")
        primary = primary.operands[0]
        self.builder.block.instructions.pop()

        expr = self.visit(ctx.children[2])

        if not isinstance(expr.type, ir.IntType):
            raise CodegenException(
                ctx.children[2].start, f"array index need to be of int type, not {type2str(expr.type)}")

        ptr = self.builder.gep(primary, [int_(0), int_(1)])

        ptr = self.builder.load(ptr)

        ptr = self.builder.gep(ptr, [int_(0), expr])
        return self.builder.load(ptr)

    def visitUnary(self, ctx: LangParser.UnaryContext):
        op = ctx.op
        primary = self.visit(ctx.primary)

        if op == LangLexer.NOT:
            primary = self.convert_to_i1(ctx, primary)
            primary = self.builder.not_(primary)

        elif op == LangLexer.PLUS or op == LangLexer.MINUS:
            if not isNumber(primary):
                raise CodegenException(
                    ctx.start, "cannot perform unary plus and minus on non numbers")
            if op == LangLexer.MINUS:
                if isinstance(primary.type, ir.IntType):
                    primary = self.builder.neg(primary)
            else:
                pass

        return primary

    def visitPre(self, ctx:LangParser.PreContext):
        op = ctx.op.text
        primary = self.visit(ctx.value)

        if not isNumber(primary):
            raise CodegenException(ctx.start, f"can only apply {op} on numbers")
        
        if not isinstance(primary, ir.LoadInstr):
            raise CodegenException(ctx.start, f"wrong type to perform {op} on")

        value = primary.type(1 if op == '++' else -1)

        r = None
        if isinstance(primary.type, ir.types._BaseFloatType):
            r = self.builder.fadd(primary, value)
        else:
            r = self.builder.add(primary, value)
        self.builder.store(r, primary.operands[0])
        return r

    def visitPost(self, ctx:LangParser.PostContext):
        op = ctx.op.text
        primary = self.visit(ctx.value)

        if not isNumber(primary):
            raise CodegenException(ctx.start, f"can only apply {op} on numbers")

        if not isinstance(primary, ir.LoadInstr):
            raise CodegenException(ctx.start, f"wrong type to perform {op} on")
        
        value = primary.type(1 if op == '++' else -1)

        r = None
        if isinstance(primary.type, ir.types._BaseFloatType):
            r = self.builder.fadd(primary, value)
        else:
            r = self.builder.add(primary, value)
        self.builder.store(r, primary.operands[0])
        return primary

    def toStr(self, ctx, value):
        if isinstance(value.type, StringType):
                return value
        elif isinstance(value.type, UnsignedType):
            if value.type != ulong:
                value = self.cast(value, ulong)
            return self.builder.call(self.runtime['tostr_ulong'], [value, self.runtime['GC_malloc_atomic']])
        elif isinstance(value.type, SignedType):
            if value.type != long_:
                value = self.cast(value, ulong)
            return self.builder.call(self.runtime['tostr_slong'], [value, self.runtime['GC_malloc_atomic']])
        elif isinstance(value.type, ir.types._BaseFloatType):
            if value.type != double_:
                value = self.cast(value, double_)
            return self.builder.call(self.runtime['tostr_double'], [value, self.runtime['GC_malloc_atomic']])
        
        raise CodegenException(ctx.start, f"dont know how to create string from {type2str(value.type)}")

    def visitMember(self, ctx: LangParser.MemberContext):
        primary = self.visit(ctx.children[0])
        name = ctx.children[2].getText()

        if name == 'sizeof':
            return ir.Constant(ulong, primary.type.get_abi_size(self.target_machine.target_data))
        elif name == 'str':
            return self.toStr(ctx, primary)
        elif isinstance(primary.type, SizedArrayType) or isinstance(primary.type, StringType):
            if not isinstance(primary, ir.LoadInstr):
                raise CodegenException(
                    ctx.start, "hle?")
            primary = primary.operands[0]
            self.builder.block.instructions.pop()
            if name == 'length':
                ptr = self.builder.gep(primary, [int_(0), int_(0)])

                return self.builder.load(ptr)
            elif name == 'ptr':
                ptr = self.builder.gep(primary, [int_(0), int_(1)])

                ptr = self.builder.load(ptr)

                return self.builder.bitcast(ptr, ptr.type.pointee.element.as_pointer())
 
            else:
                raise CodegenException(ctx.start, 'arrays have only "length" and "ptr" properties')

        struct_name = primary.type.name
        struct = self.structs[struct_name]
        try:
            idx = next(i for i, v in enumerate(struct)
                       if (lambda x: x[0] == name)(v))
        except Exception:
            raise CodegenException(
                ctx.start, f'cannot find member "{name}" of struct "{struct_name}"')

        if isinstance(primary, ir.LoadInstr):
            primary = primary.operands[0]
            self.builder.block.instructions.pop()

        ptr = self.builder.gep(primary, [ir.Constant(
            int_, 0), int_(idx)])
        return self.builder.load(ptr)

    def getVar(self, name, ctx):
        if name in self.locals:
            return self.locals[name]

        if name in self.module.globals:
            var = self.module.get_global(name)
            if not var is None:
                return var

        if name in self.templates:
            return self.templates[name]

        raise CodegenException(ctx.start, f"unknown symbol {name}")

    def visitVar(self, ctx: LangParser.VarContext):
        name = ctx.getText()
        var = self.getVar(name, ctx)

        '''if var.type.is_pointer:
            if isinstance(var.type.pointee, ir.ArrayType):
                return var'''

        if isinstance(var, ir.Function) or isinstance(var, FunctionTemplate):
            return var

        return self.builder.load(var)

    def visitParenthesis(self, ctx: LangParser.ParenthesisContext):
        return self.visit(ctx.children[1])

    def visitStructVal(self, ctx: LangParser.StructValContext):
        name = ctx.name.text

        if not name in self.structs:
            raise CodegenException(ctx.start, f'no struct with name "{name}"')

        vtype = self.module.context.get_identified_type(name)

        args = self.visit(ctx.children[2])
        if len(args) == 0:
            raise CodegenException(ctx.start, "cannot create empty struct")
        if any([not isinstance(a, ir.Constant) for a in args]):
            raise CodegenException(
                ctx.start, "struct must be built from consts elements")

        if any([not a.type == b for a, b in zip(args, vtype.elements)]):
            raise CodegenException(ctx.start, "types mismatch")

        struct = ir.Constant(vtype, [x.constant for x in args])
        return struct

    def visitAndOr(self, ctx: LangParser.AndOrContext):
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
        if isinstance(left.type, ir.IntType) and isinstance(right.type, ir.types._BaseFloatType):
            left = self.cast(left, right.type)
        elif isinstance(right.type, ir.IntType) and isinstance(left.type, ir.types._BaseFloatType):
            right = self.cast(right, left.type)
        elif isinstance(right.type, ir.types._BaseFloatType) and isinstance(left.type, ir.types._BaseFloatType):
            if int(right.type.intrinsic_name[1:]) > int(left.type.intrinsic_name[1:]):
                left = self.cast(left, right.type)
            else:
                right = self.cast(right, left.type)
        elif isinstance(left.type, ir.IntType) and isinstance(right.type, ir.IntType):
            if left.type.width > right.type.width:
                right = self.cast(right, left.type)
            elif left.type.width < right.type.width:
                left = self.cast(left, right.type)
            else:
                raise CodegenException(ctx.start, "mix of signed and unsigned values")
        #else:
        #    raise CodegenException(ctx.start, "wrong type to promote")
        return left, right

    def visitBinary(self, ctx: LangParser.BinaryContext):
        op = ctx.op.type
        left = self.visit(ctx.left)
        right = self.visit(ctx.right)

        if left.type != right.type:
            left, right = self.promote(left, right, ctx)

        if left.type == right.type:
            if isinstance(left.type, ir.IntType):
                if op == LangLexer.PLUS:
                    return self.builder.add(left, right)
                elif op == LangLexer.MINUS:
                    return self.builder.sub(left, right)
                elif op == LangLexer.MULT:
                    return self.builder.mul(left, right)
                elif op == LangLexer.DIV:
                    if isSigned(left) and isSigned(right):
                        return self.builder.sdiv(left, right)
                    elif isUnsgined(left) and isUnsgined(right):
                        return self.builder.udiv(left, right)
                    else:
                        raise CodegenException(
                            ctx.op.start, "mix between signed and unsigned values")

            elif isinstance(left.type, ir.types._BaseFloatType):
                if op == LangLexer.PLUS:
                    return self.builder.fadd(left, right)
                elif op == LangLexer.MINUS:
                    return self.builder.fsub(left, right)
                elif op == LangLexer.MULT:
                    return self.builder.fmul(left, right)
                elif op == LangLexer.DIV:
                    return self.builder.fdiv(left, right)

            elif isinstance(left.type, StringType) or isinstance(right.type, StringType):
                if op != LangLexer.PLUS:
                    raise CodegenException(ctx.op.start, "can only add to strings")
                return self.builder.call(self.runtime['string_add'], [left, right, self.runtime['GC_malloc_atomic']])
        
            elif isinstance(left.type, SizedArrayType):
                if op != LangLexer.PLUS:
                    raise CodegenException(ctx.op.start, "can only add to arrays")
                a = left.type.elements[1].pointee.element
                el_size = ir.Constant(ulong, a.get_abi_size(self.target_machine.target_data))
                return self.builder.call(self.runtime['array_add'], [left, right, el_size, self.runtime['GC_malloc']])

        else:
            #if isinstance(left.type, SizedArrayType) and isinstance(right.type, left.type.element):
            #    pass
            raise CodegenException(ctx.start, f"dont know how to perform binary operation on {type2str(left.type)} and {type2str(right.type)}")


        raise CodegenException(ctx.start, f"unsuported types in binary {type2str(left.type)} and {type2str(right.type)}")

    def visitCondBinary(self, ctx: LangParser.CondBinaryContext):
        op = ctx.op.text
        left = self.visit(ctx.left)
        right = self.visit(ctx.right)

        if left.type != right.type:
            left, right = self.promote(left, right, ctx)

        if isinstance(left.type, ir.IntType):
            if isSigned(left) and isSigned(right):
                return self.builder.icmp_signed(op, left, right)
            elif isUnsgined(left) and isUnsgined(right):
                return self.builder.icmp_unsigned(op, left, right)
            else:
                raise CodegenException(
                    ctx.op.start, "mix between signed and unsigned values")

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
        fn = self.visit(ctx.value)
        args = self.visit(ctx.arguments)

        if not isinstance(fn, ir.Function):
            if isinstance(fn, FunctionTemplate):
                types = {}
                i = 0
                for x in fn.body.arguments.children:
                    if not hasattr(x, 'symbol'):
                        name = x.getText()
                        if name in fn.types:
                            # generic
                            argtype = args[i].type
                            if name in types:
                                if types[name] != argtype:
                                    raise CodegenException(ctx.start, f'type "{name}" redefintion')
                            types[name] = argtype
                            i += 1
                # generate fn or get ready one
                template = fn
                signature = '|'.join(map(lambda x: type2str(x), types.values()))
                if signature in template.implemented:
                    fn = template.implemented[signature]
                else:
                    oldtypes = self.types
                    oldlocals = self.locals
                    oldbuilder = self.builder
                    oldname = template.body.name.text

                    self.types = types
                    template.body.name.text += str(self.get_uniq())
                    fn = self.visit(template.body)

                    template.body.name.text = oldname
                    template.implemented[signature] = fn
                    self.types = oldtypes
                    self.builder = oldbuilder
                    self.locals = oldlocals
            elif isinstance(fn.type, ir.PointerType) and isinstance(fn.type.pointee, ir.FunctionType):
                pass
            else:
                raise CodegenException(ctx.start, f'"{ctx.value.getText()}" is not a function')

        fn_args = fn.type.pointee.args
        #fn_ret = fn.type.pointee.return_type
        fn_var_arg = fn.type.pointee.var_arg
        #fnargs = fn.ftype.args

        if len(fn_args) != len(args):
            if not (fn_var_arg and len(fn_args) < len(args)):
                raise CodegenException(ctx.start, f"wrong args count, expect {len(fn_args)} got {len(args)}")

        irargs = []
        for i, arg in enumerate(args):
            arg_llvm = arg
            if isinstance(arg_llvm.type, StringType):
                if isinstance(fn_args[i], ir.PointerType):
                    if fn_args[i].type.pointee.width == 8:
                        arg_llvm = self.builder.gep(arg_llvm.operands[0], [int_(0),int_(1)])
                        arg_llvm = self.builder.load(arg_llvm)
                        arg_llvm = self.builder.bitcast(arg_llvm, fn_args[i])

            if fn_var_arg and i >= len(fn_args):
                # var arg
                if isinstance(arg_llvm.type, ir.FloatType) or isinstance(arg_llvm.type, ir.HalfType):
                    arg_llvm = self.builder.fpext(arg_llvm, double_)
            else:
                if fn_args[i] != arg_llvm.type:
                    raise CodegenException(ctx.arguments.children[i*2].start, f"argument {i+1} have wrong type, expected type {type2str(fn_args[i])} got {type2str(arg_llvm.type)}")

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

        if right.type != left.type.pointee:
            raise CodegenException(ctx.start, f"types mismatch {type2str(left.type.pointee)} != {type2str(right.type)}") 

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
            raise CodegenException(ctx.start, "unknown type for bool value")

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

        self.loops.append(w_after_block)

        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_body_block)
        self.visit(ctx.block)

        cond = self.visit(ctx.value)
        cond = self.convert_to_i1(cond, ctx)
        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_after_block)

        self.loops.pop()

    def visitForLoop(self, ctx: LangParser.ForLoopContext):
        cond = self.visit(ctx.b)
        cond = self.convert_to_i1(cond, ctx)

        self.visit(ctx.a)

        w_body_block = self.builder.append_basic_block("w_body")
        w_after_block = self.builder.append_basic_block("w_after")

        self.loops.append(w_after_block)

        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_body_block)
        self.visit(ctx.block)
        self.visit(ctx.c)

        cond = self.visit(ctx.b)
        cond = self.convert_to_i1(cond, ctx)
        self.builder.cbranch(cond, w_body_block, w_after_block)

        self.builder.position_at_start(w_after_block)

        self.loops.pop()


    def visitBreak(self, ctx:LangParser.BreakContext):
        # TODO: handle missing loop
        if not ctx.number is None:
            number = int(ctx.number.text)
            for i in range(number):
                end = self.loops.pop()
        end = self.loops.pop()
        self.builder.branch(end)

    def visitContinue(self, ctx:LangParser.ContinueContext):
        raise CodegenException(ctx.start, "continue not implemented")

    def visitDeclaration(self, ctx: LangParser.DeclarationContext):
        if ctx.name.text in self.locals:
            raise CodegenException(ctx.start, f'variable "{ctx.name.text}" redefinition')

        if ctx.vartype is None and ctx.value is None:
            raise CodegenException(ctx.start, "variable need a type")

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
            vartype = self.visit(ctx.vartype)
            value = self.visit(ctx.value)
            if vartype != value.type:
                raise CodegenException(ctx.vartype.start, f"types mismatch {type2str(vartype)} != {type2str(value.type)}")
            ptr = self.builder.alloca(value.type)
            self.builder.store(value, ptr)
            self.locals[ctx.name.text] = ptr

    def visitExpression(self, ctx: LangParser.ExpressionContext):
        return self.visit(ctx.children[0])

    def visitReturn(self, ctx: LangParser.ReturnContext):
        rtype = self.builder.function.ftype.return_type
        if ctx.value is None:
            if not isinstance(rtype, ir.VoidType):
                raise CodegenException(ctx.start, "return need to have value")
            self.builder.ret_void()
        else:
            value = self.visit(ctx.value)
            if value.type != rtype:
                raise CodegenException(
                    ctx.start, f"return need to be {type2str(rtype)}, not {type2str(value.type)}")
            self.builder.ret(value)

    def visitGlobalVar(self, ctx: LangParser.GlobalVarContext):
        value = self.visit(ctx.value)

        # TODO: add possibility to take global_variable
        if not isinstance(value, ir.Constant):
            raise CodegenException(ctx.start, "global vars need to be const")

        # TODO: check global name redefinition!
        global_var = ir.GlobalVariable(
            self.module, value.type, name=ctx.name.text)
        global_var.global_constant = False
        global_var.initializer = value

        return global_var

    def visitBasicType(self, ctx: LangParser.BasicTypeContext):
        name = ctx.getText()

        if name == "int":
            return int_
        elif name == "uint":
            return uint
        elif name == "byte":
            return byte_
        elif name == "ubyte":
            return ubyte
        elif name == "short":
            return short_
        elif name == "ushort":
            return ushort
        elif name == "long":
            return long_
        elif name == "ulong":
            return ulong
        elif name == "half":
            return half_
        elif name == "float":
            return float_
        elif name == "double":
            return double_
        elif name == "void":
            return ir.VoidType()
        elif name == "string":
            return StringType()
        elif name in self.structs:
            return self.module.context.get_identified_type(name)
        elif name in self.types:
            return self.types[name]

        raise CodegenException(ctx.start, "unknown type")

    def visitPointerType(self, ctx: LangParser.PointerTypeContext):
        typ = self.visit(ctx.children[0])
        if isinstance(typ, ir.VoidType):
            typ = voidptr
        return typ.as_pointer()

    def visitFnType(self, ctx:LangParser.FnTypeContext):
        args = self.visit(ctx.arguments)
        rettype = self.visit(ctx.ret)
        varargs = not ctx.varargs is None
        return ir.FunctionType(rettype, args, varargs).as_pointer()

    def visitArrayType(self, ctx: LangParser.ArrayTypeContext):
        typ = self.visit(ctx.children[0])
        if ctx.size == None:
            return SizedArrayType(typ)
        raise CodegenException(ctx.start, "arrays with const size not supported")
        #elements = int(ctx.size.text)
        #return ir.ArrayType(typ, elements)

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
                raise CodegenException(ctx.start, f'missing return in "{name}" function')

        self.locals = None
        self.builder = None

        return func

    def visitExternVar(self, ctx: LangParser.ExternVarContext):
        name = ctx.name.text
        vartype = self.visit(ctx.vartype)
        global_text = ir.GlobalVariable(self.module, vartype, name=name)
        global_text.linkage = 'external'
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
            raise CodegenException(ctx.start, f'struct "{name}" redefinition')

        self.structs[name] = members
        b = self.module.context.get_identified_type(name)
        b.set_body(*[x[1] for x in members])

    def visitImportLib(self, ctx:LangParser.ImportLibContext):
        name = ctx.name.text

        module = self.driver.compile_file("./stdlib/" + name + ".pclang", self.target_machine)
        for f in module.functions:
            if f.name in self.module.globals:
                if not f.name in self.runtime:
                    raise CodegenException(ctx.start, "symbol redefinition")
            else:
                self.module.add_global(f)

        for s in module.structs:
            members = module.structs[s]
            b = self.module.context.get_identified_type(s)
            b.set_body(*[x[1] for x in members])
            # TODO: check struct redefinition!
            pass
        self.templates = self.templates | module.templates

    def visitRawArgs(self, ctx: LangParser.RawArgsContext):
        if ctx.children is None:
            return []
        args = []
        for arg in ctx.children:
            if arg.symbol.text != ',':
                args.append(arg.symbol.text)
        return args

    def visitTemplate(self, ctx: LangParser.TemplateContext):
        args = self.visit(ctx.arguments)

        if not ctx.tstruct is None:
            raise CodegenException(ctx.start, "struct template not implemented")
        else:
            # TODO: redefinition
            self.templates[ctx.tfunc.name.text] = FunctionTemplate(ctx.tfunc, args)

    def visitStructValTemplate(self, ctx: LangParser.StructValTemplateContext):
        pass

    def visitCallTemplate(self, ctx: LangParser.CallTemplateContext):
        name = ctx.value.getText()
        types = self.visit(ctx.types)
        args = self.visit(ctx.arguments)

        template = self.templates[name]

        if len(types) != len(template.types):
            raise CodegenException(ctx.start, "ehh not working :(")

        # set types somehow

        oldtypes = self.types
        oldlocals = self.locals
        oldbuilder = self.builder

        self.types = {}
        fn = None
        
        for i in range(len(types)):
            self.types[template.types[i]] = types[i]

        signature = '|'.join(map(lambda x: type2str(x), self.types.values()))
        if signature in template.implemented:
            fn =template.implemented[signature]
        else:
            oldname = template.body.name.text

            template.body.name.text += str(self.get_uniq())

            fn = self.visit(template.body)

            template.body.name.text = oldname

            self.types = oldtypes
            self.builder = oldbuilder
            self.locals = oldlocals

            # TODO: check types

        return self.builder.call(fn, args)

