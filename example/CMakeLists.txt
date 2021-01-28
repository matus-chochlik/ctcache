# Copyright Matus Chochlik.
# Distributed under the Boost Software License, Version 1.0.
# See accompanying file LICENSE_1_0.txt or copy at
#  http://www.boost.org/LICENSE_1_0.txt
#
cmake_minimum_required(VERSION 3.10)
project(ctcache-example VERSION 1.0)

find_program(CLANG_TIDY_COMMAND clang-tidy)

add_executable(bad01 bad01.cpp)
target_compile_options(bad01 PRIVATE -pedantic;-Wall;-Werror)
if(CLANG_TIDY_COMMAND)
    set_target_properties(
        bad01 PROPERTIES
        CXX_CLANG_TIDY ${CLANG_TIDY_COMMAND}
    )
endif()
