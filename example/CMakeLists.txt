# Copyright Matus Chochlik.
# Distributed under the Boost Software License, Version 1.0.
# See accompanying file LICENSE_1_0.txt or copy at
#  http://www.boost.org/LICENSE_1_0.txt

cmake_minimum_required(VERSION 3.10)
project(ctcache-example VERSION 1.0)

find_program(CLANG_TIDY_COMMAND clang-tidy)

add_executable(bad01 bad01.cpp)
target_compile_options(bad01 PRIVATE -pedantic;-Wall;-Werror)

if(CLANG_TIDY_COMMAND)
    function(find_all_directories_with_clang_tidy VARIABLE)
        file(GLOB CLANG_TIDY_FILES "${CMAKE_CURRENT_SOURCE_DIR}/.clang-tidy")

        if(CLANG_TIDY_FILES)
            list(APPEND DIRECTORIES_WITH_CLANG_TIDY ${CMAKE_CURRENT_SOURCE_DIR})
        endif()

        file(GLOB ALL_PROJECT_FILES
             LIST_DIRECTORIES true
             "${CMAKE_CURRENT_SOURCE_DIR}/*"
        )

        foreach(DIRECTORY ${ALL_PROJECT_FILES})
            if(IS_DIRECTORY ${DIRECTORY})
                get_filename_component(DIR_NAME ${DIRECTORY} NAME)

                if(NOT DIR_NAME STREQUAL "build")
                    # Check if the directory contains a .clang-tidy file
                    file(GLOB CLANG_TIDY_FILES "${DIRECTORY}/.clang-tidy")

                    # If so, add the directory to `DIRECTORIES_WITH_CLANG_TIDY`
                    if(CLANG_TIDY_FILES)
                        list(APPEND DIRECTORIES_WITH_CLANG_TIDY ${DIRECTORY})
                    endif()
                endif()
            endif()
        endforeach()

        # CMake splits args up with ";" so use "*" to keep all the directories together, folders can't contain "*" in their name so this should be safe
        string(REPLACE ";" "*" DIRECTORIES_WITH_CLANG_TIDY "${DIRECTORIES_WITH_CLANG_TIDY}")

        set(${VARIABLE}
            ${DIRECTORIES_WITH_CLANG_TIDY}
            PARENT_SCOPE
        )
    endfunction()

    find_all_directories_with_clang_tidy(DIRECTORIES_WITH_CLANG_TIDY)

    if(DIRECTORIES_WITH_CLANG_TIDY)
        set_target_properties(bad01 PROPERTIES CXX_CLANG_TIDY ${CLANG_TIDY_COMMAND} --directories_with_clang_tidy=${DIRECTORIES_WITH_CLANG_TIDY})
    else()
        set_target_properties(bad01 PROPERTIES CXX_CLANG_TIDY ${CLANG_TIDY_COMMAND})
    endif()
endif()
