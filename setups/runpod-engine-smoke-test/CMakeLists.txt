# ==============================================================================
# Proposed CMakeLists.txt for snngine_v4/nn/cuda_backend/
# ==============================================================================
# Staged in setups/runpod-engine-smoke-test/ for verification on Runpod.
# Resolves the following blockers present in the original CMakeLists.txt:
# 1. Guards the 'testing_executable' target: original references ./tests/tests_main.cu
#    and ./tests/tests.cu which do not exist in snngine_v4, causing build failures.
# 2. Dynamic Python discovery: original hardcodes /usr/local/bin/python3.12 and
#    /usr/lib/x86_64-linux-gnu/libpython3.12.so.1.0, failing on Ubuntu/Runpod images
#    where Python is at /usr/bin/python3 or in /opt/venv.
# 3. Modern default CUDA architecture: defaults to SM 89 (Ada) with CLI override
#    support instead of SM 61 (Pascal 2016).
# 4. Explicit cuSPARSE linking: guarantees cusparse symbols resolve cleanly.
# ==============================================================================

cmake_minimum_required(VERSION 3.18)

project(cuda_backend LANGUAGES CXX CUDA)

set(OpenGL_GL_PREFERENCE GLVND)

# ------------------------------------------------------------------------------
# CUDA Compiler & Target Architecture
# ------------------------------------------------------------------------------
if(NOT DEFINED CMAKE_CUDA_COMPILER AND EXISTS "/usr/local/cuda/bin/nvcc")
    set(CMAKE_CUDA_COMPILER /usr/local/cuda/bin/nvcc)
endif()

if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES)
    # Default to SM 89 (Ada Lovelace) with fallback compatibility if not specified
    set(CMAKE_CUDA_ARCHITECTURES 89)
endif()

# ------------------------------------------------------------------------------
# Python & Dependency Discovery (Dynamic & Environment-Independent)
# ------------------------------------------------------------------------------
if(NOT DEFINED Python_EXECUTABLE AND NOT DEFINED PYTHON_EXECUTABLE)
    find_program(Python_EXECUTABLE NAMES python3 python3.12 python)
    if(Python_EXECUTABLE)
        set(PYTHON_EXECUTABLE "${Python_EXECUTABLE}")
    endif()
endif()

find_package(Python 3.10 COMPONENTS Interpreter Development REQUIRED)
find_package(OpenGL REQUIRED)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/src/include/
    ${CMAKE_CURRENT_SOURCE_DIR}/src/
    /usr/local/cuda/include
    /usr/local/cuda/lib64/
    ${Python_INCLUDE_DIRS}
    ${OPENGL_INCLUDE_DIR}
)

link_directories(
    /usr/local/cuda/lib64
)

set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS}
    -Xcompiler -fPIC
)

set(CUDA_SEPARABLE_COMPILATION ON)
set(CUDA_PROPAGATE_HOST_FLAGS ON)

# ------------------------------------------------------------------------------
# Target 1: snn_utils
# ------------------------------------------------------------------------------
cuda_add_library(snn_utils SHARED
    ./src/utils/utils_bindings.cu
    ./src/structures/network_structures.cpp
    ./src/utils/launch_parameters.cu
    ./src/utils/curand_states.cu
)

target_link_libraries(snn_utils
    ${Python_LIBRARIES}
)

# ------------------------------------------------------------------------------
# Target 2: snn_simulation_gpu
# ------------------------------------------------------------------------------
cuda_add_library(snn_simulation_gpu SHARED
    ./src/simulation/snn_simulation_bindings.cu
    ./src/simulation/snn_simulation.cu
)

target_link_libraries(snn_simulation_gpu
    snn_utils
    cusparse
)

# ------------------------------------------------------------------------------
# Target 3: snn_construction_gpu
# ------------------------------------------------------------------------------
cuda_add_library(snn_construction_gpu SHARED
    ./src/construction/snn_construction_bindings.cu
    ./src/construction/snn_representation.cu
    ./src/operators/connector.cu
)

target_link_libraries(snn_construction_gpu
    snn_utils
    cusparse
)

# ------------------------------------------------------------------------------
# Output Properties & Shared Library Suffixes
# ------------------------------------------------------------------------------
set_target_properties(snn_utils PROPERTIES PREFIX "")
set_target_properties(snn_construction_gpu PROPERTIES PREFIX "")
set_target_properties(snn_simulation_gpu PROPERTIES PREFIX "")

if(WIN32)
    set_target_properties(snn_utils PROPERTIES SUFFIX ".pyd")
    set_target_properties(snn_construction_gpu PROPERTIES SUFFIX ".pyd")
    set_target_properties(snn_simulation_gpu PROPERTIES SUFFIX ".pyd")
endif()

# ------------------------------------------------------------------------------
# Optional Standalone Test Executable (Guarded against missing source files)
# ------------------------------------------------------------------------------
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/tests_main.cu" AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/tests.cu")
    add_executable(testing_executable
        ./tests/tests_main.cu
        ./tests/tests.cu
    )
    target_link_libraries(testing_executable snn_utils)
    set_target_properties(testing_executable PROPERTIES PREFIX "")
    if(WIN32)
        set_target_properties(testing_executable PROPERTIES SUFFIX ".pyd")
    endif()
endif()
