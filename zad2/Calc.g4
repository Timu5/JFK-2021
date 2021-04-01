grammar Calc;


WS: [ \t\r\n]+ -> skip;

COMMENT : '/*' .*? '*/' -> skip ;
COMMENT_LINE : '//' .*? ('\n' | EOF) -> skip ;

INT   : [0-9]+;
FLOAT : ([0-9]* '.' [0-9]+) | ([0-9]+ '.' [0-9]*);
IDENT : [_a-zA-Z][_0-9a-zA-Z]*;
CHAR  : '\'' . '\'';
STRING : '"' ~('"')* '"';

PLUS  : '+';
MINUS : '-';
MULT  : '*';
DIV   : '/';
LPAREN: '(';
RPAREN: ')';
COMMA : ',';

vtype: IDENT           # basicType
    | vtype '*'        # pointerType
    | vtype ('[' ']')  # arrayType
    ;

args: (expr (COMMA expr)*)?;

primary
    : op=(PLUS | MINUS) value=primary                       # unary
    | INT                                                   # number
    | FLOAT                                                 # float
    | CHAR                                                  # char
    | STRING                                                # string
    | IDENT                                                 # var
    | '[' args ']'                                          # array
    | name=IDENT LPAREN arguments=args RPAREN               # call
    | LPAREN expr RPAREN                                    # parenthesis
    | primary '.' IDENT                                     # member
    | primary '[' expr ']'                                  # index
    ;

expr
    : left=expr op=(MULT | DIV) right=expr                  # binary
    | left=expr op=(PLUS | MINUS) right=expr                # binary
    |<assoc=right> cond=expr '?' truee=expr ':' falsee=expr # tenary
    |<assoc=right> left=expr op='=' right=expr              # assign
    | primary                                               # eprimary
    ;

statement
    : expr ';'                                              # expression
    | 'if' LPAREN value=expr RPAREN truee=statement 
                                 ('else' falsee=statement)? # conditional
    | 'while' LPAREN value=expr RPAREN block=statement      # loop
    | '{' statement* '}'                                    # block
    | 'let' name=IDENT ('=' value=expr)? ';'                # declaration
    | 'const' name=IDENT '=' value=expr ';'                 # const
    | 'return' (value=expr)? ';'                            # return
    ;

fnargs: (vtype (COMMA vtype)*)?;

function
    : 'fn' name=IDENT LPAREN arguments=fnargs RPAREN block=statement;

extern
    : 'extern' rettype=vtype name=IDENT LPAREN arguments=fnargs (COMMA varargs='...')? RPAREN ';';

program: (function | statement | extern)*;
