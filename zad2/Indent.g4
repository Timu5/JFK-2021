lexer grammar Indent;


@lexer::header{
from antlr_denter.DenterHelper import DenterHelper
from .LangParser import LangParser
}
@lexer::members {
class MyCoolDenter(DenterHelper):
    def __init__(self, lexer, nl_token, indent_token, dedent_token, ignore_eof):
        super().__init__(nl_token, indent_token, dedent_token, ignore_eof)
        self.lexer: LangLexer = lexer

    def pull_token(self):
        return super(LangLexer, self.lexer).nextToken()

denter = None

def nextToken(self):
    if not self.denter:
        self.denter = self.MyCoolDenter(self, self.NL, LangParser.INDENT, LangParser.DEDENT, False)
    return self.denter.next_token()
}