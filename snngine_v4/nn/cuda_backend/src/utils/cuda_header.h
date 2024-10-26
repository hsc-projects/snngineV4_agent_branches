#pragma once

#include <include/helper_cuda.h>
#include <stdio.h>

#include <cuda_runtime.h>

#include <cuda_gl_interop.h>

#include <curand.h>
#include <curand_kernel.h>
#include "cublas_v2.h"
#include <cusparse.h>

#define THRUST_IGNORE_DEPRECATED_CPP_DIALECT

#include <thrust/device_ptr.h>
#include <thrust/execution_policy.h>
#include <thrust/scan.h>
#include <thrust/sort.h>

#ifdef __INTELLISENSE__

#define KERNEL_ARGS2(grid, block)
#define KERNEL_ARGS3(grid, block, sh_mem)
#define KERNEL_ARGS4(grid, block, sh_mem, stream)

#else

#define KERNEL_ARGS2(grid, block) <<< grid, block >>>
#define KERNEL_ARGS3(grid, block, sh_mem) <<< grid, block, sh_mem >>>
#define KERNEL_ARGS4(grid, block, sh_mem, stream) <<< grid, block, sh_mem, stream >>>

#endif

#define WRAP(x) do {x} while (0)
#define checkCusparseErrors(x) WRAP(									\
  cusparseStatus_t err = (x);											\
  if (err != CUSPARSE_STATUS_SUCCESS) {									\
    std::cerr << "\nCusparse Error " << int(err) << " ("                \
        << cusparseGetErrorString(err) <<") at Line "                   \
        << __LINE__ << " of " << __FILE__ << ": " << #x << std::endl;   \
    exit(1);															\
  }																		\
)


/*
    (cuda versions 12.1, 12.2)
    checkCudaErrors(cudaOccupancyMaxPotentialBlockSize()) returns
        code=98(cudaErrorInvalidDeviceFunction)
    when applying calling it on kernels from other module

  printf("\n(0) .grid_size, .block_size= %d, %d", launch_grid_size, launch_block_size__); \                                                        \
  printf("\n(1) .grid_size, .block_size= %d, %d", launch_grid_size, launch_block_size__); \                                                            \


*/
//#define LAUNCH_PARAMETERS_(launch_pars, func, n_threads_x, blockSizeLimit, min_grid_size__, launch_block_size__) \
//  LaunchParameters launch_pars;  \
//  int min_grid_size__ = 0; \
//  int launch_block_size__ = 0;                                  \
//  printf("\n(0) .grid_size, .block_size= %d, %d", min_grid_size__, launch_block_size__); \
//  checkCudaErrors(cudaOccupancyMaxPotentialBlockSize( \
//    &min_grid_size__, &launch_block_size__,   \
//    (void *)func, 0, blockSizeLimit));                                \
//  printf("\n(1) .grid_size, .block_size= %d, %d", min_grid_size__, launch_block_size__); \
//  launch_pars.init_1d(launch_block_size__, n_threads_x)

#define LAUNCH_PARAMETERS(launch_pars, func, n_threads_x, blockSizeLimit) \
  LaunchParameters launch_pars;  \
  {                                                                        \
      int min_grid_size__ = 0; \
      int launch_block_size__ = 0;                                  \
      checkCudaErrors(cudaOccupancyMaxPotentialBlockSize( \
        &min_grid_size__, &launch_block_size__,   \
        (void *)func, 0, blockSizeLimit));                                \
      launch_pars.init_1d(min_grid_size__, launch_block_size__, n_threads_x);                \
  }


#define LAUNCH_PARAMETERS_B64(launch_pars, func, n_threads_x) \
    LAUNCH_PARAMETERS(launch_pars, func, n_threads_x, 64)

#define KERNEL_ARGS_L(launch) KERNEL_ARGS2(launch.grid3, launch.block3)

#define KERNEL_ARGS_IL_X(launch_pars, func, n_threads_x, blockSizeLimit) \
    LAUNCH_PARAMETERS(launch_pars, func, n_threads_x, blockSizeLimit); \
    func KERNEL_ARGS_L(launch_pars)

#define KERNEL_ARGS_B64_IL_X(launch_pars, func, n_threads_x) \
    LAUNCH_PARAMETERS_B64(launch_pars, func, n_threads_x); \
    func KERNEL_ARGS_L(launch_pars)

//  LaunchParameters launch(grid_size, block_size);

#include "utils/launch_parameters.cuh"
#include "utils/curand_states.cuh"
