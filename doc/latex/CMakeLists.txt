# Copyright Matus Chochlik.
# Distributed under the Boost Software License, Version 1.0.
# See accompanying file LICENSE_1_0.txt or copy at
#  http://www.boost.org/LICENSE_1_0.txt
#

find_program(PDFLATEX_COMMAND pdflatex)
find_program(PYTHON3_COMMAND python3)

add_custom_target(latex-doc)
add_dependencies(doc latex-doc)

macro(ctcache_generate_figure IMG_NAME GENERATOR SRC_DATA)
    if(PDFLATEX_COMMAND)
        if(PYTHON3_COMMAND)
            add_custom_command(
                OUTPUT ctcache-${IMG_NAME}.pdf
                COMMAND "${PYTHON3_COMMAND}" "-B"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/${GENERATOR}.py"
                    "-i" "${CMAKE_CURRENT_SOURCE_DIR}/data/${SRC_DATA}.json"
                    "-o" "${IMG_NAME}.pdf"
                WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
                DEPENDS
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/${GENERATOR}.py"
                    "${CMAKE_CURRENT_SOURCE_DIR}/data/${SRC_DATA}.json"
                COMMENT "Rendering ctcache-${IMG_NAME}.pdf"
            )
        endif()
    endif()
endmacro()

ctcache_generate_figure(project1_build_times plot-build-time project1_build_times)
ctcache_generate_figure(project2_build_times plot-build-time project2_build_times)

file(GENERATE
    OUTPUT "beamercolorthemectcache.sty"
    INPUT "beamercolorthemectcache.sty.in"
)

file(GENERATE
    OUTPUT "beamer_ctcache.tex"
    INPUT "beamer_ctcache.tex.in"
)

macro(ctcache_add_latex_presentation SRC_NAME)
    if(PDFLATEX_COMMAND)
        set(SRC_PATH "${CMAKE_CURRENT_SOURCE_DIR}/${SRC_NAME}.tex")

        add_custom_command(
            OUTPUT "${SRC_NAME}.tex"
            COMMAND ${CMAKE_COMMAND} -E copy_if_different "${SRC_PATH}" "./"
            WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
            DEPENDS ${SRC_PATH}
            COMMENT "Copying ${SRC_NAME} LaTeX source"
        )

        set(PRESENTATION_DEPENDS
            "${CMAKE_CURRENT_BINARY_DIR}/beamercolorthemectcache.sty"
            "${CMAKE_CURRENT_BINARY_DIR}/beamer_ctcache.tex"
            "${CMAKE_CURRENT_BINARY_DIR}/${SRC_NAME}.tex"
        )

        add_custom_target(
            ${SRC_NAME}-latex-sources
            DEPENDS ${PRESENTATION_DEPENDS}
        )

        foreach(DEPNAME ${ARGN})
            list(APPEND PRESENTATION_DEPENDS ctcache-${DEPNAME}.pdf)
        endforeach()

        add_custom_command(
            OUTPUT ctcache-${SRC_NAME}.toc
            COMMAND pdflatex
                "-shell-escape"
                "-interaction" "batchmode"
                "-halt-on-error"
                "-output-directory=${CMAKE_CURRENT_BINARY_DIR}"
                "-jobname" "ctcache-${SRC_NAME}"
                "${SRC_NAME}.tex"
            WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
            DEPENDS
                ${PRESENTATION_DEPENDS}
                ${SRC_NAME}-latex-sources
            COMMENT "Preparing ctcache-${SRC_NAME}.pdf"
        )

        add_custom_command(
            OUTPUT ctcache-${SRC_NAME}.pdf
            COMMAND pdflatex
                "-shell-escape"
                "-interaction" "batchmode"
                "-output-directory=${CMAKE_CURRENT_BINARY_DIR}"
                "-jobname" "ctcache-${SRC_NAME}"
                "${SRC_NAME}.tex"
            WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
            DEPENDS ctcache-${SRC_NAME}.toc
            COMMENT "Generating ctcache-${SRC_NAME}.pdf"
        )

        add_custom_target(
            ctcache-${SRC_NAME}-pdf
            DEPENDS ctcache-${SRC_NAME}.pdf
        )

        add_dependencies(latex-doc ctcache-${SRC_NAME}-pdf)
    endif()
endmacro()

ctcache_add_latex_presentation(
    overview
    project1_build_times
    project2_build_times
)
