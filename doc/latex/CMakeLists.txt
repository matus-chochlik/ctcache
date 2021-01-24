# Copyright Matus Chochlik.
# Distributed under the Boost Software License, Version 1.0.
# See accompanying file LICENSE_1_0.txt or copy at
#  http://www.boost.org/LICENSE_1_0.txt
#

find_program(PDFLATEX_COMMAND pdflatex)
find_program(PYTHON3_COMMAND python3)

add_custom_target(latex-doc)
add_dependencies(doc latex-doc)

macro(ctcache_generate_figure IMG_NAME GENERATOR)
    if(PDFLATEX_COMMAND)
        if(PYTHON3_COMMAND)
            set(FIG_DEPS)
            set(GEN_ARGS)
            foreach(SRC_DATA ${ARGN})
                list(APPEND GEN_ARGS "-i")
                list(APPEND GEN_ARGS "${CMAKE_CURRENT_SOURCE_DIR}/data/${SRC_DATA}.json")
                list(APPEND FIG_DEPS "${CMAKE_CURRENT_SOURCE_DIR}/data/${SRC_DATA}.json")
            endforeach()
            list(APPEND GEN_ARGS "-o")
            list(APPEND GEN_ARGS "${IMG_NAME}.pdf")
            list(APPEND FIG_DEPS "${CMAKE_CURRENT_SOURCE_DIR}/tools/${GENERATOR}.py")

            add_custom_command(
                OUTPUT ctcache-${IMG_NAME}.pdf
                COMMAND "${PYTHON3_COMMAND}" "-B"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/${GENERATOR}.py"
                    ${GEN_ARGS}
                WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
                DEPENDS ${FIG_DEPS}
                COMMENT "Rendering ctcache-${IMG_NAME}.pdf"
            )
        endif()
    endif()
endmacro()

ctcache_generate_figure(
    project1_build_times
    plot-build-time
    project1_build_times
)
ctcache_generate_figure(
    project2_build_times
    plot-build-time
    project2_build_times
)
ctcache_generate_figure(
    project3_build_times
    plot-build-time
    project3_build_times
)

ctcache_generate_figure(
    build_speedups
    plot-build-speedup
    project1_build_times
    project2_build_times
    project3_build_times
)

ctcache_generate_figure(
    p3_j4_system_load
    plot-system-load
    p3_j4_cxx_ctd
    p3_j4_cxc_ctd
    p3_j4_cxx_ctc
    p3_j4_cxc_ctc
)

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
    project3_build_times
    build_speedups
    p3_j4_system_load
)
