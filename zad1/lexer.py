from enum import Enum


class Token(Enum):
    EOF = -1
    UNKNOWN = 0

    NL = 1
    SPACE = 18
    COLON = 2
    DASH = 3

    STRING = 4
    ID = 5
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


_keywords = ["version", "services", "build", "ports",
             "image", "volumes", "enviroment", "networks", "deploy"]
_keywordsToken = [Token.VERSION, Token.SERVICES, Token.BUILD, Token.PORTS,
                  Token.IMAGE, Token.VOLUMES, Token.ENVIROMENT, Token.NETWORKS, Token.DEPLOY]

class Lexer:

    def __init__(self, input):
        self.input = input
        self.index = 0
        self.buffer = ""
        self.number = 1
        self.line = 1
        self.col = 1
        self.lastchar = ' '
        #self.lastint = ord(self.lastchar)
        self.indentation = 0
        self.new_indentation = 0
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

    def untilnl(self):
        self.buffer = ""
        while self.lastchar == "\n" or self.lastchar == '\x00':
            self.buffer += self.lastchar
            self.nextchar()

        return self.buffer

    def gettoken(self):
        
        if self.new_indentation > self.indentation:
            if self.new_indentation - self.indentation > 2:
                raise Exception("You fucking idiot!!!")
            self.indentation = self.new_indentation
            return Token.INDENT

        if self.lastchar == "\n":
            self.new_indentation = 0
            while self.nextchar() == ' ':
                self.new_indentation += 1
            if self.lastchar == '\n':
                return self.gettoken()
            return Token.NL

        if self.new_indentation < self.indentation:
            self.indentation -= 2
            return Token.DEDENT

        if self.lastchar == "\x00":
            if self.indentation != 0:
                self.new_indentation = 0
                return Token.NL
                #return self.gettoken()
            return Token.EOF

        if self.lastchar.isalpha():
            self.buffer = ""
            while self.lastchar.isalpha():
                self.buffer += self.lastchar
                self.nextchar()

            if self.buffer in _keywords:
                return _keywordsToken[_keywords.index(self.buffer)]

            return Token.ID

        elif self.lastchar.isdigit():
            value = 0.0
            exponent = 0

            while self.lastchar.isdigit():
                value = value * 10 + (ord(self.lastchar) - ord('0'))
                self.nextchar()

            if self.lastchar == '.':
                self.nextchar()
                while self.lastchar.isdigit():
                    value = value * 10 + (ord(self.lastchar) - ord('0'))
                    exponent -= 1
                    self.nextchar()

            if self.lastchar == 'e' or self.lastchar == 'E':
                sign = 1
                i = 0
                self.nextchar()
                if self.lastchar == '-':
                    sign = -1
                    self.nextchar()
                elif self.lastchar == '+':
                    # do nothing when positive :)
                    self.nextchar()

                while self.lastchar.isdigit():
                    i = i * 10 + (ord(self.lastchar) - ord('0'))
                    self.nextchar()

                exponent += sign * i

            while exponent > 0:
                value *= 10
                exponent -= 1

            while exponent < 0:
                value *= 0.1
                exponent += 1

            self.number = value

            return Token.NUMBER

        elif self.lastchar == '"':
            self.nextchar()
            self.buffer = ""
            while self.lastchar != '"' and self.lastchar != "\x00":
                self.buffer += self.lastchar
                self.nextchar()

            if self.lastchar == '\x00':
                raise "Unexpected end of file"

            self.nextchar()
            return Token.STRING

        tmp = Token.UNKNOWN

        if self.lastchar == ':':
            tmp = Token.COLON
        elif self.lastchar == '-':
            tmp = Token.DASH
        elif self.lastchar == ' ':
            tmp = Token.SPACE

        self.nextchar()
        return tmp
