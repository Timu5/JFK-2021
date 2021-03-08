from enum import Enum
import re
from collections import namedtuple

TokenTuple = namedtuple('TokenTuple', 'type line col')

class Token(Enum):
    EOF = -1
    UNKNOWN = 0

    NL = 1
    SPACE = 18
    COLON = 2
    DASH = 3

    STRING = 4
    #ID = 5
    NUMBER = 6

    VERSION = 7
    SERVICES = 8
    BUILD = 9
    PORTS = 10
    IMAGE = 11
    VOLUMES = 12
    ENVIROMENT = 13
    NETWORKS = 14
    DEPLOY = 15

    INDENT = 16
    DEDENT = 17
    STRING_PORT = 22
    STRING_VERSION = 23


_keywords = ["version", "services", "build", "ports",
             "image", "volumes", "enviroment", "networks", "deploy"]
_keywordsToken = [Token.VERSION, Token.SERVICES, Token.BUILD, Token.PORTS,
                  Token.IMAGE, Token.VOLUMES, Token.ENVIROMENT, Token.NETWORKS, Token.DEPLOY]
'''_keywords = []
_keywordsToken = []'''


def is_keyword(token):
    return token in _keywordsToken


class Lexer:

    def __init__(self, input):
        self.input = input
        self.index = 0
        self.buffer = ""
        self.line = 1
        self.col = 1
        self.lastchar = ' '
        self.indentation = 0
        self.new_indentation = 0
        self.indents = [0]
        self.nextchar()

    def nextchar(self):
        if self.index >= len(self.input) or self.input[self.index] == '\x00':
            self.lastchar = '\x00'  # EOF
        else:
            self.lastchar = self.input[self.index]
            self.index += 1

        if self.lastchar == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1

        return self.lastchar

    def unget(self):
        self.index -= 2
        self.col -= 2
        self.nextchar()

    def gettoken(self):
        return TokenTuple(type=self._gettoken(), line=self.line, col=self.col)

    def _gettoken(self):

        if self.new_indentation > self.indentation:
            self.indents.append(self.new_indentation - self.indentation)
            self.indentation = self.new_indentation
            return Token.INDENT

        if self.lastchar == "\n":
            self.new_indentation = 0
            while self.nextchar() == ' ':
                self.new_indentation += 1
            if self.lastchar == '\n':
                return self._gettoken()
            return Token.NL

        if self.new_indentation < self.indentation:
            size = self.indents.pop()
            self.indentation -= size
            if(self.indentation < 0):
                raise Exception("Indents do not match")
            return Token.DEDENT

        if self.lastchar == "\x00":
            if self.indentation != 0:
                self.new_indentation = 0
                return Token.NL
            return Token.EOF

        if self.lastchar == '"':
            self.nextchar()
            self.buffer = ""
            while self.lastchar != '"' and self.lastchar != "\x00":
                self.buffer += self.lastchar
                self.nextchar()

            if self.lastchar == '\x00':
                raise Exception("Unexpected end of file")

            self.nextchar()

            if re.match(r"^([0-9]{2,5})+(:([0-9]{2,5}))?$", self.buffer) != None:
                return Token.STRING_PORT

            if re.match(r"^[1-3]+(\.\d+)?$", self.buffer) != None:
                return Token.STRING_VERSION

            # use regex to find subtype of string

            
            return Token.STRING

        tmp = Token.UNKNOWN

        if self.lastchar == ':':
            tmp = Token.COLON
        elif self.lastchar == '-':
            tmp = Token.DASH
        elif self.lastchar == ' ':
            tmp = Token.SPACE
        else:
            #if self.lastchar.isalpha() or self.lastchar.isdigit():
            self.buffer = ""
            while self.lastchar != '\n' and self.lastchar != '\x00':
                if self.lastchar == ':':
                    self.nextchar()
                    if self.lastchar == ' ' or self.lastchar == '\n' or self.lastchar == '\x00':
                        self.unget()
                        break
                self.buffer += self.lastchar
                self.nextchar()

            if self.buffer in _keywords:
                return _keywordsToken[_keywords.index(self.buffer)]

            # use regex to find subtype of string
            if re.match(r"^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$", self.buffer) != None:
                return Token.NUMBER

            #if re.match(r"^([0-9]{2,5})+(:([0-9]{2,5}))?$", self.buffer) != None:
            #    return Token.STRING_PORT

            return Token.STRING


        self.nextchar()
        return tmp
