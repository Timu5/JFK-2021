parser grammar LangParser;

options {
	tokenVocab = LangLexer;
}

fstring: OPEN_STRING fstringElement* CLOSE_STRING;

fstringElement:
	TEXT								# rawString
	| EXPR_ENTER value = expr RPAREN	# exprString;

vtype:
	ID																			# basicType
	| vtype '*'																	# pointerType
	| vtype '[' (size = INT)? ']'												# arrayType
	| 'f' '(' arguments = fnargs (',' varargs = '...')? ')' '->' ret = vtype	# fnType;

args: (expr (COMMA expr)*)?;

primary:
	op = (PLUS | MINUS | NOT) value = primary								# unary
	| value = INT literal = ID?												# number
	| value = FLOAT literal = ID?											# float
	| CHAR																	# char
	| fstring																# string
	| ID																	# var
	| '[' args ']'															# array
	| name = ID '(' types = fnargs ')' '{' arguments = args '}'			# structValTemplate
	| 'cast' '(' vartype = vtype ')' value = primary					# cast
	| 'typeid' '(' vartype = vtype ')'									# typeid
	| value = primary '(' types = fnargs ')' '(' arguments = args ')'	# callTemplate
	| value = primary '(' arguments = args ')'							# call

expr:
	left = expr op = (MULT | DIV) right = expr							# binary
	| left = expr op = (PLUS | MINUS) right = expr						# binary
	| left = expr op = ('>' | '<' | '>=' | '<=') right = expr			# condBinary
	| left = expr op = ('==' | '!=') right = expr						# condBinary
	| left = expr op = ('and' | 'or') right = expr						# andOr
	| <assoc = right> cond = expr '?' truee = expr ':' falsee = expr	# tenary
	| <assoc = right> left = expr op = '=' right = expr					# assign
	| primary															# eprimary;

statements: (statement)+;

statement:
	expr NL # expression
	| 'if' value = expr ':' INDENT truee = statements DEDENT (
		'else' ':' INDENT falsee = statements DEDENT
	)?																				# conditional
	| 'while' value = expr ':' INDENT block = statements DEDENT						# loop
	| 'for' a = expr ';' b = expr ';' c = expr ':' INDENT block = statements DEDENT	# forLoop
	| 'break' (number = INT)? NL													# break
	| 'continue' NL																	# continue
	| name = ID (
		(':' vartype = vtype)
		| (':' vartype = vtype '=' value = expr)
		| (':=' value = expr)
	) NL												# declaration
	| 'const' name = ID (':=' | '=') value = expr NL	# const
	| 'return' (value = expr)? NL						# return
	| 'pass' NL											# pass;

globalVar:
	name = ID (
		((':' vartype = vtype)? ('=' value = expr)?)
		| (':=' value = expr)
	) NL;

fnargs: (vtype (COMMA vtype)*)?;

fnargsnamed: (ID ':' vtype (COMMA ID ':' vtype)*)?;

function:
	'fn' name = ID LPAREN arguments = fnargsnamed (
		COMMA varargs = '...'
	)? RPAREN '->' rettype = vtype ':' INDENT block = statements DEDENT;

externVar: 'extern' name = ID ':' vartype = vtype NL;

extern:
	'extern' name = ID LPAREN arguments = fnargs (
		COMMA varargs = '...'
	)? RPAREN '->' rettype = vtype NL;

structMember:
	name = ID ':' membertype = vtype NL	# structField
	| func = function					# structMethod;
structMembers: (structMember)+;
struct:
	'struct' name = ID ':' INDENT members = structMembers DEDENT;

importLib: IMPORT name = ID NL;

rawArgs: (ID (COMMA ID)*)?;

template:
	'template' '(' arguments = rawArgs ')' NL (
		tfunc = function
		| tstruct = struct
	);

program: (
		importLib
		| function
		| extern
		| externVar
		| globalVar
		| struct
		| template
	)* EOF;

