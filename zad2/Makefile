BUILDDIR=build
FILENAME=manual

all:
	java -Xmx500M -cp "/usr/local/lib/antlr-4.9.1-complete.jar:$CLASSPATH" org.antlr.v4.Tool -Dlanguage=Python3 -o generated LangLexer.g4
	java -Xmx500M -cp "/usr/local/lib/antlr-4.9.1-complete.jar:$CLASSPATH" org.antlr.v4.Tool -visitor -Dlanguage=Python3 -o generated LangParser.g4

report:
	mkdir $(BUILDDIR) -p
	pandoc $(FILENAME).md \
	--from=markdown+raw_tex+tex_math_single_backslash+tex_math_dollars \
	--to=latex \
	--output=$(BUILDDIR)/$(FILENAME).pdf \
	--pdf-engine=xelatex \
	--filter pandoc-citeproc \
	-V lang=pl-PL	