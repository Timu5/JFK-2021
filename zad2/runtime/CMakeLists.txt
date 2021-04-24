cmake_minimum_required(VERSION 3.10)

add_subdirectory(bdwgc)

project(runtime)

add_library(runtime SHARED array.c tostr.c)

target_link_libraries(runtime gc)