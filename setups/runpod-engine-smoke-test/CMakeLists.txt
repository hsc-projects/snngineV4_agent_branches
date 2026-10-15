cmake_minimum_required(VERSION 3.18)

project(cuda_backend)

set(OpenGL_GL_PREFERENCE GLVND)

set(CMAKE_CUDA_COMPILER /usr/local/cuda/bin/nvcc)
set(CMAKE_C_COMPILER /usr/bin/gcc)
set(CMAKE_CXX_COMPILER /usr/bin/g++)

enable_language(CUDA)
find_package(CUDA REQUIRED)

if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES)
  set(CMAKE_CUDA_ARCHITECTURES 89)
endif()

set(Python_EXECUTABLE /usr/bin/python3)
find_package(Python 3.12 EXACT COMPONENTS Interpreter Development REQUIRED)
find_package(OpenGL REQUIRED)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/src/include/
    ${CMAKE_CURRENT_SOURCE_DIR}/src/
    /usr/local/cuda/include
    /usr/local/cuda/lib64/
    ${Python_INCLUDE_DIRS}
    ${OPENGL_INCLUDE_DIR}
)

link_directories(/usr/local/cuda/lib64)

set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS};
    -Xcompiler
    -fPIC
)

set(CUDA_SEPARABLE_COMPILATION ON)
set(CUDA_PROPAGATE_HOST_FLAGS ON)

cuda_add_library(snn_utils SHARED
    ./src/utils/utils_bindings.cu
    ./src/structures/network_structures.cpp
    ./src/utils/launch_parameters.cu
    ./src/utils/curand_states.cu
)

cuda_add_library(snn_simulation_gpu SHARED
    ./src/simulation/snn_simulation_bindings.cu
    ./src/simulation/snn_simulation.cu
)

cuda_add_library(snn_construction_gpu SHARED
    ./src/construction/snn_construction_bindings.cu
    ./src/construction/snn_representation.cu
    ./src/operators/connector.cu
)

target_link_libraries(snn_utils
    ${Python_LIBRARIES}
)

target_link_libraries(snn_simulation_gpu
    snn_utils
    ${CUDA_cusparse_LIBRARY}
    cusparse
)

target_link_libraries(snn_construction_gpu
    snn_utils
    ${CUDA_cusparse_LIBRARY}
    cusparse
)

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/tests_main.cu")
    add_executable(testing_executable
        ./tests/tests_main.cu
        ./tests/tests.cu
    )
    target_link_libraries(testing_executable
        snn_utils
    )
    set_target_properties(testing_executable PROPERTIES PREFIX "")
endif()

set_target_properties(snn_utils PROPERTIES PREFIX "")
set_target_properties(snn_construction_gpu PROPERTIES PREFIX "")
set_target_properties(snn_simulation_gpu PROPERTIES PREFIX "")

if(WIN32)
    set_target_properties(snn_utils PROPERTIES SUFFIX ".pyd")
    set_target_properties(snn_construction_gpu PROPERTIES SUFFIX ".pyd")
    set_target_properties(snn_simulation_gpu PROPERTIES SUFFIX ".pyd")
endif()
