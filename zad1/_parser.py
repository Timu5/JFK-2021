from lexer import Token


class Parser:

    def __init__(self, lexer):
        self.lexer = lexer
        self.lasttoken = Token.EOF
        self.nexttoken()

    def nexttoken(self):
        self.lasttoken = self.lexer.gettoken()
        return self.lasttoken

    def match(self, token_type):
        if self.lasttoken.type != token_type:
            line = self.lasttoken.line
            col = self.lasttoken.col
            raise Exception(
                f"Unexpected token, expect {token_type.name} got {self.lasttoken.type.name} at line {line} column {col}")

    def nextmatch(self, token_type):
        self.nexttoken()
        self.match(token_type)

    def warning(self, token):
        line = token.line
        col = token.col
        buf = token.buf
        if token.type != Token.STRING:
            buf = token.type.name
        print(f"Warning unknown element \"{buf}\" at line {line} column {col}")

    def root(self):

        if self.lasttoken.type == Token.VERSION:
            self.version()

        elif self.lasttoken.type == Token.SERVICES:
            self.services()

        elif self.lasttoken.type == Token.VOLUMES:
            self.nextmatch(Token.COLON)
            if self.nexttoken().type == Token.SPACE:
                self.nexttoken()
            
            self.generic()

        elif self.lasttoken.type == Token.NETWORKS:
            self.nextmatch(Token.COLON)
            if self.nexttoken().type == Token.SPACE:
                self.nexttoken()

            self.generic()

        elif self.lasttoken.type == Token.EOF:
            return

        elif self.lasttoken.type == Token.STRING:
            self.warning(self.lasttoken)
            self.nextmatch(Token.COLON)
            if self.nexttoken().type == Token.SPACE:
                self.nexttoken()

            self.generic()

        elif self.lasttoken.type == Token.NL or self.lasttoken == Token.SPACE:
            self.nexttoken()
        else:
            raise Exception(
                f"Unexpected token {self.lasttoken.type.name} in root element at line {self.lasttoken.line} column {self.lasttoken.col}")

        self.root()
        self.match(Token.EOF)

    def version(self):
        self.nextmatch(Token.COLON)
        self.nextmatch(Token.SPACE)
        self.nextmatch(Token.STRING_VERSION)
        self.nextmatch(Token.NL)
        self.nexttoken()

    def services(self):
        self.nextmatch(Token.COLON)
        self.nexttoken()

        if self.lasttoken.type == Token.SPACE:
            self.nexttoken()

        if self.lasttoken.type == Token.NL:
            self.nextmatch(Token.INDENT)
            self.nexttoken()

            self.service_element()

            self.match(Token.DEDENT)
            self.nexttoken()

    def service_element(self):
        while self.lasttoken.type == Token.STRING:
            self.match(Token.STRING)
            self.nextmatch(Token.COLON)
            self.nexttoken()
            if self.lasttoken.type == Token.SPACE:
                self.nexttoken()
            self.match(Token.NL)
            self.nextmatch(Token.INDENT)
            self.nexttoken()

            self.subservice()

            self.match(Token.DEDENT)
            self.nexttoken()

    def subservice(self):
        keywords = [Token.IMAGE, Token.PORTS, Token.NETWORKS,
                    Token.DEPLOY, Token.VOLUMES, Token.BUILD,
                    Token.ENVIRONMENT]

        while self.lasttoken.type in keywords or self.lasttoken.type == Token.STRING:
            name = self.lasttoken
            self.nextmatch(Token.COLON)

            if self.nexttoken().type == Token.SPACE:
                self.nexttoken()

            if name.type == Token.IMAGE:
                self.match(Token.STRING)
                self.nextmatch(Token.NL)
                self.nexttoken()

            elif name.type == Token.BUILD:
                self.match(Token.STRING)
                self.nextmatch(Token.NL)
                self.nexttoken()

            elif name.type == Token.PORTS:
                self.match(Token.NL)
                self.nextmatch(Token.INDENT)
                self.nexttoken()

                self.list_ports()

                self.match(Token.DEDENT)
                self.nexttoken()

            elif name.type == Token.NETWORKS:
                self.match(Token.NL)
                self.nextmatch(Token.INDENT)
                self.nexttoken()

                self.list_string()

                self.match(Token.DEDENT)
                self.nexttoken()

            elif name.type == Token.DEPLOY:
                self.generic()

            elif name.type == Token.VOLUMES:
                self.match(Token.NL)
                self.nextmatch(Token.INDENT)
                self.nexttoken()

                self.list_string()

                self.match(Token.DEDENT)
                self.nexttoken()

            elif name.type == Token.ENVIRONMENT:
                self.match(Token.NL)
                self.nextmatch(Token.INDENT)
                self.nexttoken()

                self.list_string()

                self.match(Token.DEDENT)
                self.nexttoken()

            elif name.type == Token.STRING:
                self.warning(name)
                self.generic()

    def list_ports(self):
        while self.lasttoken.type == Token.DASH:
            self.nextmatch(Token.SPACE)
            self.nextmatch(Token.STRING_PORT)
            self.nextmatch(Token.NL)
            self.nexttoken()

    def list_string(self):
        while self.lasttoken.type == Token.DASH:
            self.nextmatch(Token.SPACE)
            self.nextmatch(Token.STRING)
            self.nextmatch(Token.NL)
            self.nexttoken()

    def generic(self):
        if self.lasttoken.type == Token.STRING_VERSION or self.lasttoken.type == Token.STRING_PORT or self.lasttoken.type == Token.STRING:
            self.nextmatch(Token.NL)
            self.nexttoken()
            # handle string
        elif self.lasttoken.type == Token.NUMBER:
            self.nextmatch(Token.NL)
            self.nexttoken()
            # handle int
        elif self.lasttoken.type == Token.NL:
            self.nexttoken()
            if self.lasttoken.type == Token.INDENT:
                self.nexttoken()
                if self.lasttoken.type == Token.DASH:
                    # list
                    self.list()
                    self.match(Token.DEDENT)
                    self.nexttoken()
                elif self.lasttoken.type == Token.STRING:
                    # map
                    self.map()
                    self.match(Token.DEDENT)
                    self.nexttoken()
            else:
                # null
                pass

            pass

    def list(self):
        self.match(Token.DASH)
        while self.lasttoken.type == Token.DASH:
            self.match(Token.DASH)
            if self.nexttoken().type == Token.SPACE:
                self.nexttoken()
            self.generic()

    def map(self):
        self.match(Token.STRING)
        while self.lasttoken.type == Token.STRING:
            self.match(Token.STRING)
            self.nextmatch(Token.COLON)
            if self.nexttoken().type == Token.SPACE:
                self.nexttoken()
            self.generic()
