from lexer import Lexer
from _parser import Parser

class Colors:
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

test = open('compose.yaml',mode='r').read()

lex = Lexer(test)

par = Parser(lex)

try:
    par.root()
    print(f"{Colors.OKGREEN}Valid!{Colors.ENDC}")
except Exception as e:
    print(e.args[0])
    print(f"{Colors.FAIL}Not valid!{Colors.ENDC}")
