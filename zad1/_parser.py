from lexer import Token, is_keyword


class Parser:

    def __init__(self, lexer):
        self.lexer = lexer
        self.lasttoken = Token.EOF
        self.nexttoken()

    def nexttoken(self):
        self.lasttoken = None
        self.lasttoken = self.lexer.gettoken()
        #print(self.lasttoken)
        return self.lasttoken

    def match(self, token_type):
        #print(f"match {token_type} {self.lasttoken}")
        if self.lasttoken.type != token_type:
            line = self.lasttoken.line
            col = self.lasttoken.col
            raise Exception(
                f"Unexpected token, expect {token_type.name} got {self.lasttoken.type.name} at line {line} column {col}")

    def warning(self, token):
        line = self.lexer.line
        col = self.lexer.col
        buf = self.lexer.buffer
        if token != Token.STRING:
            buf = token.type.name
        print(f"Warning unknown element: {buf} at line {line} column {col}")

    def nextmatch(self, token_type):
        self.nexttoken()
        self.match(token_type)

    def root(self):

        if self.lasttoken.type == Token.VERSION:
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
            self.nextmatch(Token.STRING_VERSION)
            self.nextmatch(Token.NL)
            self.nexttoken()

        elif self.lasttoken.type == Token.SERVICES:
            self.nextmatch(Token.COLON)
            self.nexttoken()

            if self.lasttoken.type == Token.SPACE:
                self.nexttoken()

            if self.lasttoken.type == Token.NL:
                self.nextmatch(Token.INDENT)
                self.nexttoken()
                while self.lasttoken.type == Token.STRING:
                    self.service()
                self.match(Token.DEDENT)
                self.nexttoken()

        elif self.lasttoken.type == Token.VOLUMES:
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
            self.nexttoken()
            self.generic()

            # TODO: finish
            print("TODO ROOT VOLUMES")

        elif self.lasttoken.type == Token.NETWORKS:
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
            self.nexttoken()
            self.generic()

            # TODO: finish
            print("TODO ROOT NETWORKS")

        elif self.lasttoken.type == Token.EOF:
            return

        elif self.lasttoken.type == Token.STRING:
            self.warning(self.lasttoken)
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
            self.nexttoken()
            self.generic()

        # elif self.lasttoken.type == Token.NL or self.lasttoken == Token.SPACE:
        #    self.nexttoken()
        else:
            raise Exception(
                f"Unexpected token {self.lasttoken} at line {self.lexer.line} column {self.lexer.col}")

        self.root()
        self.match(Token.EOF)

    def service(self):
        keywords = [Token.IMAGE, Token.PORTS, Token.NETWORKS,
                    Token.DEPLOY, Token.VOLUMES, Token.BUILD,
                    Token.ENVIROMENT]
        self.match(Token.STRING)
        self.nextmatch(Token.COLON)
        self.nexttoken()
        if self.lasttoken.type == Token.SPACE:
            self.nexttoken()
        self.match(Token.NL)
        self.nextmatch(Token.INDENT)
        self.nexttoken()

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

                while self.lasttoken.type == Token.DASH:
                    self.nextmatch(Token.SPACE)
                    self.nextmatch(Token.STRING_PORT)
                    self.nextmatch(Token.NL)
                    self.nexttoken()

                self.match(Token.DEDENT)
                self.nexttoken()

            elif name.type == Token.NETWORKS:
                # self.nexttoken()
                self.generic()
                print("TODO NETWORKS")

            elif name.type == Token.DEPLOY:
                # self.nexttoken()
                self.generic()
                print("TODO DEPLOY")

            elif name.type == Token.VOLUMES:
                # self.nexttoken()
                # self.generic()
                self.ylist()
                print("TODO VOLUMES")
                # list of string!

            elif name.type == Token.ENVIROMENT:
                # list of strings
                # or map of strings
                self.ylist()
                print("TODO ENVIROMENT")

            elif name.type == Token.STRING:
                # self.nexttoken()
                self.warning(name)
                self.generic()

        self.match(Token.DEDENT)
        self.nexttoken()

    def ylist(self):
        self.match(Token.NL)
        self.nextmatch(Token.INDENT)

        self.nexttoken()

        while self.lasttoken.type != Token.DEDENT:
            self.match(Token.DASH)
            if(self.nexttoken().type == Token.SPACE):
                self.nexttoken()
            # self.nextmatch(Token.STRING)
            self.nextmatch(Token.NL)
            self.nexttoken()

        self.match(Token.DEDENT)
        self.nexttoken()

    def generic(self):
        if self.lasttoken.type == Token.STRING:
            self.nextmatch(Token.NL)
            self.nexttoken()
            print("string")
            # handle string
        elif self.lasttoken.type == Token.NUMBER:
            self.nextmatch(Token.NL)
            self.nexttoken()
            print("number")
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
                print("null")
                # null
                pass

            pass

    def list(self):
        self.match(Token.DASH)
        print("list")
        while self.lasttoken.type == Token.DASH:
            self.match(Token.DASH)
            self.nextmatch(Token.SPACE)
            self.nexttoken()
            self.generic()

    def map(self):
        self.match(Token.STRING)
        print("map")
        while self.lasttoken.type == Token.STRING:
            self.match(Token.STRING)
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
            self.nexttoken()
            self.generic()
