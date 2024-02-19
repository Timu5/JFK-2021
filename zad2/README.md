# PCLANG Compiler

## Overview

PCLANG is a compiler written in Python that utilizes LLVM(llvmlite package) as its backend. It is designed for a statically typed language with a Python-like syntax. The language supports a variety of features including classes, templates, garbage collector, string interpolation, pointers, imports, and C interoperability.

## Features

- **Python-Like Syntax:** PCLANG adopts a syntax that is reminiscent of Python, making it easy for developers familiar with Python to grasp the language quickly.

- **Static Typing:** The language is statically typed, ensuring robust type checking during compile-time, leading to more reliable code.

- **Classes:** PCLANG supports the creation and usage of classes, facilitating object-oriented programming paradigms.

- **Templates:** The language includes template support, allowing for generic programming and code reuse.

- **Garbage Collector:** PCLANG includes a garbage collector to automatically manage memory, reducing the burden on developers for memory management.

- **String Interpolation:** String interpolation simplifies the process of embedding variables within string literals, enhancing readability and conciseness.

- **Pointers:** Developers can use pointers to directly manipulate memory, providing low-level memory access when needed.

- **Imports:** PCLANG supports importing external modules or libraries, enabling code organization and reuse.

- **C Interoperability:** The compiler facilitates interoperability with C, allowing developers to integrate existing C code or leverage C libraries seamlessly.

## Examples

Also checkout `examples` directory. You can find more detailed manual in Polish by looking at `manual.md` file. 

### Class Definition:
```python
class Rectangle:
    width: int
    height: int

    fn init(width: int, height: int) -> void:
        this.width = width
        this.height = height
    
    fn area() -> void:
        return this.width * this.height 
```

### Template Usage:
```python
template(T)
class Pair:
    first: T
    second: T

    fn init(first: T, second: T) -> void:
        this.first = first
        this.second = second

# Instantiate a pair of integers
pair_of_ints = Pair(int){5, 10}
```

### String Interpolation:
```python
name = "Alice"
age = 30
println(f"Hello, my name is \(name) and I am \(age) years old.")
```

### Struct Definition with Operator Overloading:
```python
struct vector3:
    x: double
    y: double
    z: double

    fn str() -> string:
        return "\(this.x), \(this.y), \(this.z)"

    fn binop(right: vector3, op: int) -> vector3:
        result := vector3{0.0, 0.0, 0.0}
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
    println(myvector) # use .str for conversion

    r := myvector + myvector2
    println(r) # 1.5, 3.0, 5.0
```

### C Interoperability:
```python
# Declare an external C function
extern atoi(byte*) -> int

# Use the C function in PCLANG code
str = "abc"
result = atoi(str.ptr)
```
