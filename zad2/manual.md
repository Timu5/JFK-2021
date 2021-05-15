---
title: "PCLANG - Instrukcja języka"
date: \today
author: "Mateusz Muszyński 317719"
#bibliography: "bibliography.bib"
csl: "https://raw.githubusercontent.com/citation-style-language/styles/master/harvard-anglia-ruskin-university.csl"
link-citations: true
urlcolor: "blue"
header-includes: \usepackage{gensymb}
...

## Gramatyka

Poniżej znajduje sie pełna gramatyka języka.

```

fstring: '"' fstringElement* '"'

fstringElement:
	| TEXT
	| '\(' expr ')'

vtype:
	| ID														
	| vtype '*'									
	| vtype '[' ']'
	| 'fn' '(' fnargs (',' '...')? ')' '->' vtype
	| ID '(' fnargs ')'

args: (expr (',' expr)*)?
fnargs: (vtype (',' vtype)*)?
fnargsnamed: (ID ':' vtype (',' ID ':' vtype)*)?
rawargs: (ID (',' ID)*)?

primary:
	| (PLUS | MINUS | NOT) primary
	| INT ID?
	| FLOAT ID?
	| CHAR
	| fstring
	| ID
	| '[' args ']'
	| ID '(' fnargs ')' '{' args '}'
	| ID '{' args '}'
	| 'cast' '(' vtype ')' primary
	| 'typeid' '(' vtype ')'
	| primary '(' fnargs ')' '(' args ')'
	| primary '(' args ')'
	| '(' expr ')'
	| primary '.' (ID | TYPEID)
	| primary '[' expr ']'
	| '&' primary
	| '*' primary
	| ('++' | '--') primary
	| primary ('++' | '--')

expr:
	| expr ('*' | '/') expr
	| expr ('+' | '-') expr
	| expr ('>' | '<' | '>=' | '<=') expr
	| expr ('==' | '!=') expr
	| expr ('and' | 'or') expr
	| expr '?' expr ':' expr
	| expr '=' expr
	| primary

statements: (statement)+

statement:
	| expr NL
	| 'if' expr ':' INDENT statements DEDENT
		('else' ':' INDENT statements DEDENT)?
	| 'while' expr ':' INDENT statements DEDENT
	| 'for' expr ';' expr ';' expr ':' INDENT statements DEDENT
	| 'break' (number = INT)? NL
	| 'continue' NL
	| ID (
		(':' vtype)
		| (':' vtype '=' expr)
		| (':=' expr)
	) NL
	| 'return' (expr)? NL
	| 'pass' NL

globalVar:
	ID (
		(':' vtype)
		| (':' vtype '=' expr)
		| (':=' expr)
	) NL;

function:
	'fn' ID '(' fnargsnamed (',' '...')? ')' '->' vtype ':'
		INDENT statements DEDENT;

externVar: 'extern' ID ':' vtype NL

extern:
	'extern' ID '(' fnargs (',' '...')? ')' '->' vtype NL;

structMember:
	| ID ':' vtype NL
	| function

structMembers: (structMember)+

struct:
	('struct' | 'class') ID ('(' ID ')')? ':'
    		INDENT structMembers DEDENT

importLib: IMPORT ID NL

template:
	'template' '(' rawargs ')' NL (function | struct);

program: (
		importLib
		| function
		| extern
		| externVar
		| globalVar
		| struct
		| template
	)* EOF
```

\newpage

## Komentarze

Występują dwa typy komentarzy jedno linijkowe rozpoczynające sie od znaku `#` a kończące na znaku nowej lini oraz wielolinijkowe rozpoczynające sie od `#=` a kończące na `=#`.

```
# to jest komentarz
#= to jest
wiekszy komentarz
=#
```

## Importowanie

Aby moć posługiwać sie funkcjami z biblioteki standardowej należy zaimportować odpowiedni moduł przy użyciu polecanie `import nazwa`.

```
import stdio # zawiera print, println oraz readln
import conv # zawiera parseInt, parseDouble oraz parseFloat
```

## Punkt wejścia

Każda aplikacja musi posiadać funkcje `main` o prototypie odpowiadającym prototypowi w języku C.

```
fn main(argc: int, argv: byte**) -> int:
    # kod programu    
    return 1
```

## Typy podstawowe i zmienne

Występują następujące typy podstawowe:

```
x_int: int = 0
x_short: short = 0s
x_long: long = 0l
x_byte: byte = 0b

x_uint: int = 0
x_ushort: ushort = 0us
x_ulong: ulong = 0ul
x_ubyte: byte = 0b

x_half: half = 0.0h
x_float: float = 0.0f
x_double: double = 0.0
```

Przy deklarowaniu zmiennej podawanie typu jest opcjonalne, gdy go nie ma typ jest dedukowany na bazie wyrażenia po prawej stronie:

```
y := 1.0 # double
z := 123ul # ulong
```

Typ `byte` można podać w postaci znaku:

```
a := 'x'
b := '\n'
```

## Wejście-wyjście

W module `stdio` występują następujące funkcje:

```
print("Hello ") # wypisanie na ekran
println("world") # wypisanie na ekran z nową linią

name := readln() # odczytanie lini z stdin
```

## Arytmetyka

Język obsługuje podstawę operacje arytmetyczne:

```
a := x * y
b := x / y
c := x + y
d := x - y
e := x++
f := --x
g := -x
h := (x+x)*(y+y)
i := x>y?x:y
```

## Tablice

Można tworzyć tablice, pobierać jej długość i elementy oraz modyfikować ich wartość. Ponad to tablice można łączyć ze sobą.


```
x := [1,2,3]

println(x.length) # wypisze długość tablicy
println(x[2]) # wypisze 3 element tablicy

x[1] = 0 # ustawi 2 element na wartość 0

y := [10,11,12]
z := x + y # z = [1,2,3,10,11,12]
```

## Łańcuchy znaków

Łańcuchy znaków opierają sie o tablice, zatem maja te same właściwości, elementem charakterystycznym jest to, ze zawsze na końcu łańcucha posiadają one dodatkowy znak '\0' dzięki czemu można je przekazywać do funkcji języka C.

```
x := "abc"

println(x.length) # wypisze długość stringa
println(x[2]) # wypisze 3 element stringa

x[1] = 'X' # ustawi 2 znak na 'X'

y := "def"
z := x + y # z = "abcdef"
```


## Instrukcje warunkowe

Występuje w wariancie z `else' lub bez.


```
if 0.3f + 0.6f != 0.9f:
    println("Known problem with floating points numbers :/")

if 1 == 1 + 2:
    print("ok")
else:
    print("not ok")

```

## Pętla

Do dyspozycji mamy pętle `while` oraz dodatkowe polecenie `break` z możliwością łamania zewnętrznych pętli.

```
    i := 0
    while i < 2:
        println(i)
        i++


    while 1 == 1:
        break
```

## Tworzenie funkcji

Funkcje tworzymy tak samo jak punkt wejścia programu, podajemy jej nazwę, argumenty z typami oraz typ zwracany. Z pętli można wyjść używając polecenia `return`.

```
fn fib(n: int) -> int:
    if n <= 1:
        return n 
    return fib(n - 1) + fib(n - 2)
```

## Struktury

Struktury to wartości złożone przekazywane przez wartość. Można dostać sie do składowych przy użyciu operatora `'.'`.

```
struct vector3:
    x: double
    y: double
    z: double

# ...
    myvector := vector3{1.0, 2.0, 3.0}
	println(myvector.x)
	myvector.y = 10.0
```

## Klasy

Klasy w odróżnieniu od struktur przekazywane sa przez referencje, dodatkowo mogą posiadać one konstruktor i być rozszerzane.

```
class foo:
    value: int

    fn init() -> void:
        this.100

class bar(foo):
    value2: double

    fn init(a: double) -> void:
        this.200
        this.value2 = a

# ...
    a := foo{}
    b := bar{1.0}
```

## Wskaźniki

Wskaźniki działa podobnie do ich odpowiedników w języku C.

```
x := 1
z := &x
*z = 2 # x = 2
```

## Interpolacja stringów

Możliwe jest wstawienie w środku stringa dowolnego wyrażenia `expr`, język zajmie sie konwersją oraz złączeniem do postaci wynikowego łańcucha znaków.

```
a := 10
println("a = \(a)")
println("2+2 = \(2+2)")
println("\(a+2) is 4")
println("fib(10) is \(fib(10)) and maybe more")
```

## Przeciążanie operatów

Istnieje możliwość przeciążenia operatów binarych i `.str` w klasach oraz srukturach. 


```
struct vector3:
    x: double
    y: double
    z: double

    fn str() -> string:
        return "\(this.x), \(this.y), \(this.z)"

    fn binop(right: vector3, op: int) -> vector3:
        result := vector3{0.0,0.0,0.0}
        if op == cast(int)'+':
            result.x = this.x + right.x
            result.y = this.y + right.y
            result.z = this.z + right.z
        else:
            println("Unknown operation '\(op)'")
        return result

# ...
    myvector := vector3{1.0, 2.0, 3.0}
    myvector2 := vector3{0.5, 1.0, 2.0}
    println(myvector) # używa .str do konwersji

    r := myvector + myvector2
    println(r) # 1.5, 3.0, 5.0
```

## Funkcje z C

Aby móć korzystać z funkcji języka C należy podać jej prototyp poprzedzony słowem `extern`.

```
extern puts(byte*) -> int
# ...
    puts("abcdef".ptr)
```

## Szablony

Szablony funkcji pozwalają na tworzenie funkcji, które mogą przyjąć dowolny typ.

```
template(T)
fn println(input: T) -> void:
    puts(input.str)

#...
	println(int)(1)
    println(1.0)
    println("abc")
```

Szablony struktur i klas pozwalają na uogólnianie typów złożonych.

```
template(T)
class myclass:
    a: T

    fn init(x:T) -> void:
        this.a = x * 2

    fn str() -> string:
        return "myclass: \(this.a)"

#...
    a := myclass(int){1}
    println(a)

    b := myclass(double){2.0}
    println(b)
```