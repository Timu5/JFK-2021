#include <stdio.h>
#include <string.h>
#include "tostr.h"

DLLEXPORT array_t tostr_ulong(uint64_t value, void *gc_malloc(size_t))
{
    char buffer[25];
    size_t size = sprintf(buffer, "%lu", value);
    char *ptr = (char *)gc_malloc(size + 1);
    memcpy(ptr, buffer, size);
    ptr[size] = 0;
    return (array_t){size, ptr};
}

DLLEXPORT array_t tostr_slong(int64_t value, void *gc_malloc(size_t))
{
    char buffer[25];
    size_t size = sprintf(buffer, "%li", value);
    char *ptr = (char *)gc_malloc(size + 1);
    memcpy(ptr, buffer, size);
    ptr[size] = 0;
    return (array_t){size, ptr};
}

DLLEXPORT array_t tostr_double(double value, void *gc_malloc(size_t))
{
    char buffer[64];
    size_t size = sprintf(buffer, "%f", value);
    char *ptr = (char *)gc_malloc(size + 1);
    memcpy(ptr, buffer, size);
    ptr[size] = 0;
    return (array_t){size, ptr};
}