#pragma once

#include <stdlib.h>

//#define DLLEXPORT __declspec(dllexport) 
#define DLLEXPORT 

struct array_s {
    size_t size;
    void * ptr;
};

typedef struct array_s array_t;

DLLEXPORT array_t array_add(array_t one, array_t two, size_t el_size, void* gc_malloc(size_t));
DLLEXPORT array_t string_add(array_t one, array_t two, void* gc_malloc(size_t));

