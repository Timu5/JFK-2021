lexer grammar LangLexer;

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
ESCAPE:
	'\\\''
	| '\\"'
	| '\\\\'
	| '\\n'
	| '\\r'
	| '\\t'
	| '\\b'
	| '\\f'
	| '\\0'
	| ('\\x' [a-fA-F0-9][a-fA-F0-9]);
CHAR: '\'' (~'\\' | ESCAPE) '\'';

PLUS: '+';
DPLUS: '++';
MINUS: '-';
DMINUS: '--';
MULT: '*';
DIV: '/';
LPAREN: '(' -> pushMode(DEFAULT_MODE);
RPAREN: ')' -> popMode;
LBRACKET: '[';
RBRACKET: ']';
LCHEVRON: '<';
RCHEVRON: '>';
LBRACE: '{';
RBRACE: '}';
AMPER: '&';
COMMA: ',';
QUERY: '?';
DOT: '.';
TDOT: '...';
COLON: ':';
SEMICOLON: ';';
EQUAL: '=';
DEQUAL: '==';
NOTEQUAL: '!=';
ASSIGN: ':=';
LEQUAL: '<=';
GEQUAL: '>=';
ARROW: '->';
NOT: 'not';
CAST: 'cast';
TYPEID: 'typeid';
AND: 'and';
OR: 'or';
CONST: 'const';
BREAK: 'break';
CONTRIUNE: 'continue';
RETURN: 'return';
PASS: 'pass';
FN: 'fn';
F: 'f';
STRUCT: 'struct';
EXTERN: 'extern';
IF: 'if';
ELSE: 'else';
WHILE: 'while';
FOR: 'for';
IMPORT: 'import';
TEMPLATE: 'template';
SLASH: '\\';
ID: [_a-zA-Z]([0-9a-zA-Z][0-9a-zA-Z]*)?;

OPEN_STRING: '"' -> pushMode(IN_STRING);

mode IN_STRING;

EXPR_ENTER: '\\(' -> pushMode(DEFAULT_MODE);
TEXT: (~('\\' | '"') | ESCAPE)+;

CLOSE_STRING: '"' -> popMode;

