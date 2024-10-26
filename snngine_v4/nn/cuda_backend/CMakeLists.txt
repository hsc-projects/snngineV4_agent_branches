cmake_minimum_required(VERSION 3.6)

project(cuda_backend )

#set(OpenGL_GL_PREFERENCE LEGACY)
set(OpenGL_GL_PREFERENCE GLVND)

set(CMAKE_CUDA_COMPILER /usr/local/cuda/bin/nvcc)
enable_language(CUDA)
find_package(CUDA REQUIRED)
# find_library(${CUDA_cusparse_LIBRARY} PATHS "/usr/local/cuda/lib64" NO_DEFAULT_PATH)

if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES)
  set(CMAKE_CUDA_ARCHITECTURES 61)
endif()


#find_package(PythonInterp 3.11 REQUIRED)
#find_package(PythonLibs 3.11 REQUIRED)
SET(PYTHON_EXECUTABLE "/usr/local/bin/python3.12")
set(PYTHON_LIBRARY "/usr/lib/x86_64-linux-gnu/libpython3.12.so.1.0")
set(PYTHON_INCLUDE_DIR "/usr/include/python3.12")
#set(PYTHON_INCLUDE_DIRS "/usr/include/python3.12")
set(PYTHON_INCLUDE_PATH "/usr/include/python3.12")

find_package(Python 3.12 COMPONENTS Interpreter Development REQUIRED)
#find_package(PythonInterp 3.12 REQUIRED)
find_package(PythonLibs 3.12 REQUIRED)

find_package(OpenGL REQUIRED)

#get_filename_component(PROJECT_INC_DIRECTORY ../../../../../../inc ABSOLUTE)

include_directories(
    ./src/
    ./tests/
    /usr/local/cuda/lib64/
    ${PYTHON_INCLUDE_DIR}
    ${PYTHON_INCLUDE_DIRS}
#    ${PROJECT_INC_DIRECTORY}
    ${OPENGL_INCLUDE_DIR}
)

link_directories(
    /usr/local/cuda/lib64
#    "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.5/libs/x64"
)


#if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
#    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
#endif()

set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS}; -Xcompiler -fPIC)


set(CUDA_SEPARABLE_COMPILATION ON)
#set(CUDA_PROPAGATE_HOST_FLAGS OFF)
set(CUDA_PROPAGATE_HOST_FLAGS ON)

cuda_add_library(snn_utils SHARED
        ./src/utils/utils_bindings.cu
        ./src/structures/network_structures.cpp
        ./src/utils/launch_parameters.cu
        ./src/utils/curand_states.cu)

#add_library(snn_utils SHARED
#        ./src/utils/utils_bindings.cu
#        ./src/structures/network_structures.cpp
#        ./src/utils/launch_parameters.cu
#        ./src/utils/curand_states.cu)

cuda_add_library(
    snn_simulation_gpu SHARED
    ./src/simulation/snn_simulation_bindings.cu
    ./src/simulation/snn_simulation.cu)

#add_library(
#    snn_simulation_gpu SHARED
#    ./src/simulation/snn_simulation_bindings.cu
#    ./src/simulation/snn_simulation.cu)

cuda_add_library(
    snn_construction_gpu SHARED
        ./src/construction/snn_construction_bindings.cu
        ./src/construction/snn_representation.cu
        ./src/operators/connector.cu)

#add_library(
#    snn_construction_gpu SHARED
#        ./src/construction/snn_construction_bindings.cu
#        ./src/construction/snn_representation.cu
#        ./src/operators/connector.cu)

target_link_libraries(
        snn_utils
         ${PYTHON_LIBRARIES}
)

target_link_libraries(
    snn_simulation_gpu
        snn_utils
        ${CUDA_cusparse_LIBRARY}
        # ${PYTHON_LIBRARIES}
)
#
target_link_libraries(
    snn_construction_gpu
        snn_utils
        ${CUDA_cusparse_LIBRARY}
        # ${PYTHON_LIBRARIES}
)


add_executable(
        testing_executable
        ./tests/tests_main.cu
        ./tests/tests.cu
        )
target_link_libraries(
        testing_executable
        snn_utils)


set_target_properties(snn_utils PROPERTIES PREFIX "")
set_target_properties(testing_executable PROPERTIES PREFIX "")
set_target_properties(snn_construction_gpu PROPERTIES PREFIX "")
set_target_properties(snn_simulation_gpu PROPERTIES PREFIX "")

#set_target_properties(snn_construction_gpu PROPERTIES
#        CUDA_SEPARABLE_COMPILATION ON)
#set_target_properties(snn_simulation_gpu PROPERTIES
#        CUDA_SEPARABLE_COMPILATION ON)

IF (WIN32)
    set_target_properties(testing_executable PROPERTIES SUFFIX ".pyd")
    set_target_properties(snn_utils PROPERTIES SUFFIX ".pyd")
    set_target_properties(snn_construction_gpu PROPERTIES SUFFIX ".pyd")
    set_target_properties(snn_simulation_gpu PROPERTIES SUFFIX ".pyd")
ENDIF()
