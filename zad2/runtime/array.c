#include <string.h>
#include <stdio.h>
//#include "bdwgc/include/gc.h"
#include "array.h"


DLLEXPORT array_t array_add(array_t one, array_t two, size_t el_size, void* gc_malloc(size_t))
{
    size_t new_size = one.size + two.size;
    void *new_ptr = gc_malloc(new_size * el_size);
    
    memcpy(new_ptr, one.ptr, one.size * el_size);
    memcpy((void *)((long long)new_ptr + el_size * one.size), two.ptr, two.size * el_size);
    
    return (array_t){new_size, new_ptr};
}
