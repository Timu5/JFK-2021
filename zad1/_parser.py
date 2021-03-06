from lexer import Token, is_keyword


class Parser:

    def __init__(self, lexer):
        self.lexer = lexer
        self.lasttoken = Token.EOF
        self.nexttoken()

    def nexttoken(self):
        self.lasttoken = self.lexer.gettoken()
        print(self.lasttoken)
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
        #self.map()
        
        if self.lasttoken == Token.VERSION:
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
            self.nextmatch(Token.STRING_VERSION)
            self.nextmatch(Token.NL)
            self.nexttoken()
        elif self.lasttoken == Token.SERVICES:
            self.nextmatch(Token.COLON)
            self.nexttoken()
            if self.lasttoken == Token.SPACE:
                self.nexttoken()
            if self.lasttoken == Token.NL:
                self.nextmatch(Token.INDENT)
                self.nexttoken()
                while self.lasttoken == Token.STRING:
                    self.service()
                self.match(Token.DEDENT)
                self.nexttoken()
        elif self.lasttoken == Token.VOLUMES:
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
            self.nexttoken()
            self.generic()

            # TODO: finish

        elif self.lasttoken == Token.NETWORKS:
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
            self.nexttoken()
            self.generic()

            # TODO: finish

        elif self.lasttoken == Token.EOF:
            return
        elif self.lasttoken == Token.STRING:
            print("Warning!")
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
            self.nexttoken()
            self.generic()
            
        #elif self.lasttoken == Token.NL or self.lasttoken == Token.SPACE:
        #    self.nexttoken()
        else:
            raise Exception(
                f"Unexpected token {self.lasttoken} at line {self.lexer.line} column {self.lexer.col}")

        self.root()
        self.match(Token.EOF)

    def service(self):
        keywords = [Token.IMAGE, Token.PORTS, Token.NETWORKS, Token.DEPLOY, Token.VOLUMES]
        self.match(Token.STRING)
        self.nextmatch(Token.COLON)
        if self.nexttoken() == Token.SPACE:
            self.nexttoken()
        self.match(Token.NL)
        self.nextmatch(Token.INDENT)
        self.nexttoken()

        while self.lasttoken in keywords or self.lasttoken == Token.STRING:
            name = self.lasttoken
            self.nextmatch(Token.COLON)
            if self.nexttoken() == Token.SPACE:
                self.nexttoken()
            if name == Token.IMAGE:
                self.match(Token.STRING)
                self.nextmatch(Token.NL)
                self.nexttoken()
            elif name == Token.PORTS:
                self.match(Token.NL)
                self.nextmatch(Token.INDENT)
                self.nexttoken()
                while self.lasttoken == Token.DASH:
                    self.nextmatch(Token.SPACE)
                    self.nextmatch(Token.STRING_PORT)
                    self.nextmatch(Token.NL)
                    self.nexttoken()
                self.match(Token.DEDENT)
                self.nexttoken()
            elif name == Token.NETWORKS:
                #self.nexttoken()
                self.generic()
                print("TODO")
            elif name == Token.DEPLOY:
                #self.nexttoken()
                self.generic()
                print("TODO")
            elif name == Token.VOLUMES:
                #self.nexttoken()
                self.generic()
                print("TODO")
            elif name == Token.STRING:
                #self.nexttoken()
                print("Warning!")
                self.generic()

        self.match(Token.DEDENT)
        self.nexttoken()

    def ylist(self):
        self.match(Token.NL)
        self.nextmatch(Token.INDENT)

        self.nexttoken()

        while self.lasttoken != Token.DEDENT:
            self.match(Token.DASH)
            if(self.nexttoken() == Token.SPACE):
                self.nexttoken()
            #self.nextmatch(Token.STRING)
            self.nextmatch(Token.NL)
            self.nexttoken()

        self.match(Token.DEDENT)
        self.nexttoken()


    def generic(self):
        if(self.lasttoken == Token.STRING):
            self.nextmatch(Token.NL)
            self.nexttoken()
            print("string")
            # handle string
        elif(self.lasttoken == Token.NUMBER):
            self.nextmatch(Token.NL)
            self.nexttoken()
            print("number")
            # handle int
        elif(self.lasttoken == Token.NL):
            self.nexttoken()
            if self.lasttoken == Token.INDENT:
                self.nexttoken()
                if self.lasttoken == Token.DASH:
                    # list
                    self.list()
                    self.match(Token.DEDENT)
                    self.nexttoken()
                elif self.lasttoken == Token.STRING:
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
        while self.lasttoken == Token.DASH:
            self.match(Token.DASH)
            self.nextmatch(Token.SPACE)
            self.nexttoken()
            self.generic()

    def map(self):
        self.match(Token.STRING)
        print("map")
        while self.lasttoken == Token.STRING:
            self.match(Token.STRING)
            self.nextmatch(Token.COLON)
            self.nextmatch(Token.SPACE)
            self.nexttoken()
            self.generic()