from lexer import Token

class Parser:

    def __init__(self, lexer):
        self.lexer = lexer
        self.lasttoken = Token.EOF
        self.nexttoken()

    def nexttoken(self):
        self.lasttoken = self.lexer.gettoken()
        return self.lasttoken

    def match(self, token):
        if self.lasttoken != token:
            line = self.lexer.line
            col = self.lexer.col
            raise Exception(
                f"Unexpected token, expect {token.name} got {self.lasttoken.name} at line {line} column {col}")

    def nextmatch(self, token):
        self.nexttoken()
        self.match(token)

    def root(self):
        if self.lasttoken == Token.VERSION:
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
            self.nextmatch(Token.STRING)
            self.nextmatch(Token.NL)
        elif self.lasttoken == Token.SERVICES:
            self.nextmatch(Token.COLON)
            self.nexttoken()
            if self.lasttoken == Token.SPACE:
                self.nexttoken()
            if self.lasttoken == Token.NL:
                self.nextmatch(Token.INDENT)
                self.nexttoken()
                self.service()
                self.match(Token.DEDENT)
                self.nexttoken()
        elif self.lasttoken == Token.VOLUMES:
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
        elif self.lasttoken == Token.NETWORKS:
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
        elif self.lasttoken == Token.EOF:
            return
        elif self.lasttoken == Token.NL or self.lasttoken == Token.SPACE:
            self.nexttoken()
        else:
            raise Exception(f"the fuck is that {self.lasttoken} {self.lexer.line} {self.lexer.col}")

        self.root()

    def service(self):
        keywords = [Token.IMAGE, Token.PORTS, Token.NETWORKS, Token.DEPLOY]
        self.match(Token.ID)
        self.nextmatch(Token.COLON)
        self.nextmatch(Token.NL)
        self.nextmatch(Token.INDENT)
        self.nexttoken()

        while self.lasttoken in keywords:
            name = self.lasttoken
            self.nextmatch(Token.COLON)
            self.nexttoken()
            if self.lasttoken == Token.SPACE:
                self.nexttoken()
            if name == Token.IMAGE:
                self.match(Token.ID)
                self.nextmatch(Token.NL)
                self.nexttoken()
            elif name == Token.PORTS:
                self.nextmatch(Token.NL)
                self.nextmatch(Token.INDENT)

                while self.lasttoken == Token.DASH:
                    self.nextmatch(Token.INDENT)
                    self.nextmatch(Token.NL)

                self.nextmatch(Token.DDDENT)

        self.match(Token.DEDENT)
        self.nexttoken()
