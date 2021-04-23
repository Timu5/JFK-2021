grammar Lang;

tokens {
	INDENT,
	DEDENT
}

import Indent;

NL: ('\r'? '\n' ' '*);

WS: ' '+ -> skip;

COMMENT: '#=' .*? '=#' -> skip;
COMMENT_LINE: '#' (~('\n'))* -> skip;

INT: '-'? [0-9]+;
FLOAT: '-'? ([0-9]* '.' [0-9]+) | ([0-9]+ '.' [0-9]*);
ID: [_a-zA-Z][_0-9a-zA-Z]*;
ESCAPE: '\\\'' | '\\"' | '\\\\' | '\\n' | '\\r'  | '\\t' | '\\b' | '\\f' |  '\\0' | ('\\x' [a-fA-F0-9][a-fA-F0-9]);
CHAR: '\'' (~'\\'|ESCAPE) '\'';
STRING: '"' (~('"')|ESCAPE)* '"';

PLUS: '+';
MINUS: '-';
MULT: '*';
DIV: '/';
LPAREN: '(';
RPAREN: ')';
COMMA: ',';
NOT: 'not';

vtype:
	ID								# basicType
	| vtype '*'						# pointerType
	| vtype '[' (size = INT)? ']'	# arrayType;

args: (expr (COMMA expr)*)?;

primary:
	op = (PLUS | MINUS | NOT) value = primary			# unary
	| value = INT literal = ID?							# number
	| value = FLOAT literal = ID?						# float
	| CHAR												# char
	| STRING											# string
	| ID												# var
	| '[' args ']'										# array
	| name = ID '{' args '}'							# structVal
	| 'cast' '(' vartype = vtype ')' value = primary	# cast
	| name = ID LPAREN arguments = args RPAREN			# call
	| LPAREN expr RPAREN								# parenthesis
	| primary '.' ID									# member
	| primary '[' expr ']'								# index
	| '&' value = primary								# address
	| '*' value = primary								# deref;

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
	| 'break'																		# break
	| 'continue'																	# continue
	| name = ID (
		((':' vartype = vtype)? ('=' value = expr)?)
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

structMember: name = ID ':' membertype = vtype;
structMembers: (structMember NL)+;
struct:
	'struct' name = ID ':' INDENT members = structMembers DEDENT;

importLib: 'import' name = ID NL;


