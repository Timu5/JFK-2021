from lexer import *
#from jsonparser import Parser

test = 'version: "3.9"\n  \n  b:\nc:\n  d:\n    e:'

lex = Lexer(test)
#par = Parser(lex)

#print(par.json())

tok = Token.UNKNOWN

while tok != Token.EOF:
    tok = lex.gettoken()
    print(tok.name)

