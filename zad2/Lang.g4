grammar Lang;

tokens { INDENT, DEDENT }

import Indent;

NL: ('\r'? '\n' ' '*);

WS: ' '+ -> skip;

COMMENT : '#=' .*? '=#' -> skip ;
COMMENT_LINE : '#' .*? ('\n' | EOF) -> skip ;

INT   : [0-9]+;
FLOAT : ([0-9]* '.' [0-9]+) | ([0-9]+ '.' [0-9]*);
ID : [_a-zA-Z][_0-9a-zA-Z]*;
CHAR  : '\'' . '\'';
STRING : '"' ~('"')* '"';

PLUS  : '+';
MINUS : '-';
MULT  : '*';
DIV   : '/';
LPAREN: '(';
RPAREN: ')';
COMMA : ',';

vtype: ID                     # basicType
    | vtype '*'                  # pointerType
    | vtype '[' (size=INT)? ']'  # arrayType
    ;

args: (expr (COMMA expr)*)?;

primary
    : op=(PLUS | MINUS) value=primary                       # unary
    | value=INT literal=ID?                              # number
    | value=FLOAT literal=ID?                            # float
    | CHAR                                                  # char
    | STRING                                                # string
    | ID                                                 # var
    | '[' args ']'                                          # array
    | name=ID '{' args '}'                               # structVal
    | 'cast' '(' vtype ')' primary                          # cast
    | name=ID LPAREN arguments=args RPAREN               # call
    | LPAREN expr RPAREN                                    # parenthesis
    | primary '.' ID                                     # member
    | primary '[' expr ']'                                  # index
    | '&' name=ID                                        # address
    | '*' name=ID                                        # deref
    ;

expr
    : left=expr op=(MULT | DIV) right=expr                  # binary
    | left=expr op=(PLUS | MINUS) right=expr                # binary
    | left=expr op=('>' | '<' | '>=' | '<=') right=expr     # condBinary
    | left=expr op=('==' | '!=') right=expr                 # condBinary
    |<assoc=right> cond=expr '?' truee=expr ':' falsee=expr # tenary
    |<assoc=right> left=expr op='=' right=expr              # assign
    | primary                                               # eprimary
    ;

statements: (statement NL)+;

statement
    : expr                                              # expression
    | 'if' value=expr ':' INDENT truee=statements DEDENT 
      ('else' ':' INDENT falsee=statements DEDENT)?      # conditional
    | 'while' value=expr ':' INDENT block=statements DEDENT  # loop
    | 'for' a=expr ';' b=expr ';' c=expr ':' INDENT 
                                       block=statements DEDENT      # forLoop
    | name=ID (((':' vartype=vtype)? ('=' value=expr)?)|(':=' value=expr)) # declaration
    | 'const' name=ID (':='|'=') value=expr                 # const
    | 'return' (value=expr)?                            # return
    ;

globalVar: 'let' name=ID ('=' value=expr)? NL;

fnargs: (vtype (COMMA vtype)*)?;

fnargsnamed: (vtype ID (COMMA vtype ID)*)?;

function
    : 'fn' rettype=vtype name=ID LPAREN arguments=fnargsnamed (COMMA varargs='...')? RPAREN ':' INDENT block=statements DEDENT;

externVar
    : 'extern' vartype=vtype name=ID NL;

extern
    : 'extern' rettype=vtype name=ID LPAREN arguments=fnargs (COMMA varargs='...')? RPAREN NL;

structMember: membertype=vtype name=ID;
structMembers: (structMember NL)+ ;
struct: 'struct' name=ID ':' INDENT members=structMembers DEDENT;

program: (function | extern | externVar | globalVar | struct)* EOF;

