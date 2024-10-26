#pragma once

#include "utils/cpp_header.h"
#include "utils/cuda_header.h"


int test_printing2();

void print_theoretical_occupancy(
	int block_size,
	const void* kernel
);


struct LaunchParameters
{
	dim3 block3;
	dim3 grid3;

	int max_block_size{-1};			// The launch configurator returned block size
	int min_max_grid_size{-1};		// The minimum grid3 size needed to achieve the
							// maximum occupancy for a full device launch
//	int grid_size{-1};			// The actual grid3 size needed, based on input size

//	void* func;

	LaunchParameters();

//	LaunchParameters(
//		int n_threads_x,
//		const void* init_func,
//		int dynamicSMemSize = 0,
//		int blockSizeLimit = 0
//	);
    LaunchParameters(
            int min_max_grid_size_,
            int block_size,
            int n_threads_x
    );

    void init_1d(
//            int grid_size,
            int min_max_grid_size_,
            int block_size,
            int n_threads_x
//            int block_size_limit = 64
    );

	LaunchParameters(
		int grid_width,
		int grid_height,
		int grid_depth,
		int blockdim_width,
		int blockdim_height,
		int blockdim_depth
	);



//	void init_sizes(
//		int n_threads_x,
//		const void* init_func,
//		int dynamicSMemSize = 0,
//		int blockSizeLimit = 0
//	);

	// LaunchParameters(
	// 	int n_threads_x, int n_threads_y,
	// 	void* init_func,
	// 	int block_dim_x = 128, int block_dim_y = 1);

	void print_info();
};