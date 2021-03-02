from lexer import *
from _parser import Parser

test = 'version: "3.9"\nservices: \n  test:\n    image: costam\n'

lex = Lexer(test)

par = Parser(lex)

par.root()
print("Valid!")

'''tok = Token.UNKNOWN

while tok != Token.EOF:
    tok = lex.gettoken()
    print(tok.name)

'''