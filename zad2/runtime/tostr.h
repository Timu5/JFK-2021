#pragma once

#include <stdlib.h>
#include <stdint.h>
#include "array.h"

DLLEXPORT array_t tostr_ulong(uint64_t value, void* gc_malloc(size_t));
DLLEXPORT array_t tostr_slong(int64_t value, void* gc_malloc(size_t));
DLLEXPORT array_t tostr_double(double value, void* gc_malloc(size_t));

