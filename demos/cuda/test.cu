

#include <stdio.h>
#include <assert.h>
#include <cuda.h>

#include "test.h"

#define N 624
#define M 397
#define MATRIX_A 0x9908b0dfUL
#define UPPER_MASK 0x80000000UL
#define LOWER_MASK 0x7fffffffUL

#define DIFFLEN 2688
#define REALDIFFLEN 81792
#define NUMCAND 3072
#define ORISIZ 81776

#define DEVLEN (DIFFLEN * NUMCAND)


__device__ void init_gengrk(unsigned int s, unsigned int* mt)
{
	mt[0]= s & 0xffffffffUL;
	unsigned int mti;
	for (mti=1; mti<N; mti++) {
		mt[mti] = (1812433253UL * (mt[mti-1] ^ (mt[mti-1] >> 30)) + mti);
		mt[mti] &= 0xffffffffUL;
	}
	mt[N] = mti;
}
__device__ void init_by_seed(unsigned int seed, unsigned int* mt) {
	int i, j, k;
	init_gengrk(19650218UL, mt);
	i=1; j=0;
	k = (N>1 ? N : 1);
	for (; k; k--) {
		mt[i] = (mt[i] ^ ((mt[i-1] ^ (mt[i-1] >> 30)) * 1664525UL)) + seed + j;
		mt[i] &= 0xffffffffUL;
		i++; j++;
		if (i>=N) { mt[0] = mt[N-1]; i=1; }
		if (j>=1) j=0;
	}
	for (k=N-1; k; k--) {
		mt[i] = (mt[i] ^ ((mt[i-1] ^ (mt[i-1] >> 30)) * 1566083941UL)) - i;
		mt[i] &= 0xffffffffUL;
		i++;
		if (i>=N) { mt[0] = mt[N-1]; i=1; }
	}

	mt[0] = 0x80000000UL;
}

__device__ void init_by_array(unsigned int init_key[], unsigned int key_length, unsigned int* mt) {
	int i, j, k;
	init_gengrk(19650218UL, mt);
	i=1; j=0;
	k = (N>key_length ? N : key_length);
	for (; k; k--) {
		mt[i] = (mt[i] ^ ((mt[i-1] ^ (mt[i-1] >> 30)) * 1664525UL)) + init_key[j] + j;
		mt[i] &= 0xffffffffUL;
		i++; j++;
		if (i>=N) { mt[0] = mt[N-1]; i=1; }
		if (j>=key_length) j=0;
	}
	for (k=N-1; k; k--) {
		mt[i] = (mt[i] ^ ((mt[i-1] ^ (mt[i-1] >> 30)) * 1566083941UL)) - i;
		mt[i] &= 0xffffffffUL;
		i++;
		if (i>=N) { mt[0] = mt[N-1]; i=1; }
	}

	mt[0] = 0x80000000UL;
}

__device__ unsigned int gengrk_int32(unsigned int* mt)
{
	unsigned int y;
	if (mt[N] >= N) {
		int kk;

		for (kk=0;kk<N-M;kk++) {
			y = (mt[kk]&UPPER_MASK)|(mt[kk+1]&LOWER_MASK);
			mt[kk] = mt[kk+M] ^ (y >> 1) ^ (y & 0x1UL ? MATRIX_A : 0x0UL);
		}
		for (;kk<N-1;kk++) {
			y = (mt[kk]&UPPER_MASK)|(mt[kk+1]&LOWER_MASK);
			mt[kk] = mt[kk+(M-N)] ^ (y >> 1) ^ (y & 0x1UL ? MATRIX_A : 0x0UL);
		}
		y = (mt[N-1]&UPPER_MASK)|(mt[0]&LOWER_MASK);
		mt[N-1] = mt[M-1] ^ (y >> 1) ^ (y & 0x1UL ? MATRIX_A : 0x0UL);
		mt[N] = 0;
	}

	y = mt[ mt[N] ++ ];

	y ^= (y >> 11);
	y ^= (y << 7) & 0x9d2c5680UL;
	y ^= (y << 15) & 0xefc60000UL;
	y ^= (y >> 18);

	return y;
}

__global__ void init_grk(unsigned int off, unsigned int* buf) {
	unsigned int idx = (blockIdx.x * blockDim.x + threadIdx.x);

	unsigned int seed = (idx + off * NUMCAND) & 0xffffffffU;
	unsigned int ft[N + 1];
	init_by_array(&seed, 1, ft);

	for (int i = 0; i < DIFFLEN; ++i) {
		unsigned int k = 0;
		for (int j = 0; j < 32; ++j) {
			unsigned int a = gengrk_int32(ft);
			gengrk_int32(ft);
			unsigned int u = a > 2147483648;

			if (i*32 + j < ORISIZ)
				k += u << j;
		}
		buf[i + idx * DIFFLEN] = k;
	}
}

__global__ void eval_arr(unsigned int* grk_buf, unsigned int* result, unsigned int* iter) {
	//unsigned int idx = blockIdx.x * blockDim.x + threadIdx.x;

	__shared__ unsigned int cop[384];

	unsigned int idx = blockIdx.x * blockDim.x + threadIdx.x;
	__syncthreads();

	unsigned int cnt = 0;
	for (unsigned int kk = 0; kk < DIFFLEN; kk += 384) {

		cop[threadIdx.x] = grk_buf[threadIdx.x + kk];
		__syncthreads();

		for (unsigned int ii = 0; ii < 384; ++ii) {

			unsigned int n = cop[ii] & iter[  idx + NUMCAND * (ii + kk)];
			//cnt += __popc(n);
			while (n) {
				cnt++;
				n &= (n - 1);
			}
			/*n = n - ((n >> 1) & 0x55555555);
			n = (n & 0x33333333) + ((n >> 2) & 0x33333333);
			cnt += ((n + (n >> 4) & 0xF0F0F0F) * 0x1010101) >> 24;*/
		}
		__syncthreads();
	}
	result[idx] = cnt;
}

int testcuda()
{
	// compare ARRLEN seeds at once
	unsigned int nblocks = NUMCAND / 384;
	unsigned int nthreads = 384;

	unsigned int *grk_buf = NULL;
	unsigned int *device_result = NULL;
	unsigned int *ref = NULL;
	unsigned int *host_result = NULL;

	host_result = (unsigned int*) malloc(NUMCAND * sizeof(unsigned int));
	cudaMalloc((void **) &device_result, NUMCAND * sizeof(unsigned int));

	// init grk_buf with n*m values at once
	cudaMalloc((void **) &grk_buf, NUMCAND * DIFFLEN *  sizeof(unsigned int));

	dim3 dim_grid(nblocks, 1, 1);
	dim3 dim_block(nthreads, 1, 1);

	cudaMalloc((void **) &ref, DEVLEN * sizeof(unsigned int));
	//cudaMemcpy(ref, vec,  DEVLEN * sizeof(unsigned int), cudaMemcpyHostToDevice);

	unsigned int best = 520;
	unsigned int bestidx = 0;

	//for (unsigned int n = 0; n < 10; ++n;


/*
int deviceCount;
cudaGetDeviceCount(&deviceCount);
printf("device count %d\n", deviceCount);

cudaDeviceProp dP;
cudaGetDeviceProperties(&dP, NULL);
//printf("Max threads per block: %d\n", dP.maxThreadsPerBlock);
//printf("Max Threads DIM: %d x %d x %d\n", dP.maxThreadsDim[0], dP.maxThreadsDim[1], dP.maxThreadsDim[2]);
//printf("Max Grid Size: %d x %d x %d\n", dP.maxGridSize[0], dP.maxGridSize[1], dP.maxGridSize[2]);

cudaDeviceProp* pDeviceProp = &dP;

     printf( "\nDevice Name \t - %s ", pDeviceProp->name );  
     printf( "\n**************************************");  
     printf( "\nTotal Global Memory\t\t -%d KB", pDeviceProp->totalGlobalMem/1024 );  
     printf( "\nShared memory available per block \t - %d KB", pDeviceProp->sharedMemPerBlock/1024 );  
     printf( "\nNumber of registers per thread block \t - %d", pDeviceProp->regsPerBlock );  
     printf( "\nWarp size in threads \t - %d", pDeviceProp->warpSize );  
     printf( "\nMemory Pitch \t - %d bytes", pDeviceProp->memPitch );  
     printf( "\nMaximum threads per block \t - %d", pDeviceProp->maxThreadsPerBlock );  
     printf( "\nMaximum Thread Dimension (block) \t - %d %d %d", pDeviceProp->maxThreadsDim[0], pDeviceProp->maxThreadsDim[1], pDeviceProp->maxThreadsDim[2] );  
     printf( "\nMaximum Thread Dimension (grid) \t - %d %d %d", pDeviceProp->maxGridSize[0], pDeviceProp->maxGridSize[1], pDeviceProp->maxGridSize[2] );  
     printf( "\nTotal constant memory \t - %d bytes", pDeviceProp->totalConstMem );  
     printf( "\nCUDA ver \t - %d.%d", pDeviceProp->major, pDeviceProp->minor );  
     printf( "\nClock rate \t - %d KHz", pDeviceProp->clockRate );  
     printf( "\nTexture Alignment \t - %d bytes", pDeviceProp->textureAlignment );  
     printf( "\nDevice Overlap \t - %s", pDeviceProp-> deviceOverlap?"Allowed":"Not Allowed" );  
     printf( "\nNumber of Multi processors \t - %d\n", pDeviceProp->multiProcessorCount );  

*/

/*
	for (unsigned int n = 0; n < 30000; ++n) {
	//for (unsigned int n = 50; n < 100; ++n) {

		if (n % 10 == 0) { printf("# iter %d\n", n); fflush(stdout); }

		init_grk <<< dim_grid, dim_block >>> (n, grk_buf);
		for (unsigned int i = 0; i < NUMCAND; ++i) {
			eval_arr <<< dim_grid, dim_block >>> (grk_buf + i * DIFFLEN, device_result, ref);
			cudaMemcpy(host_result, device_result, NUMCAND * sizeof(unsigned int), cudaMemcpyDeviceToHost);

			unsigned int s1 = 0;
			unsigned int s2 = 0;
			for (unsigned int k = 0; k < NUMCAND; ++k) {
				if (host_result[k] > s1) s1 = host_result[k];
				else if (valz[k] - host_result[k] > s2) s2 = valz[k] - host_result[k];
			}
			if (s1 + s2 >= 530) {
				if ((s1 + s2) > best) {
					best = s1 + s2;
					bestidx = i + n * NUMCAND;
				}
				unsigned int ss1 = 0;
				unsigned int ss2 = 0;
				unsigned int sss1 = 0;
				unsigned int sss2 = 0;
				for (unsigned int k = 0; k < NUMCAND; ++k) {
					if      (host_result[k] >= s1          ) { s1 = host_result[k];           ss1 = seedz[k]; sss1 = seedz_off[k]; }
					else if (valz[k] - host_result[k] >= s2) { s2 = valz[k] - host_result[k]; ss2 = seedz[k]; sss2 = seedz_off[k]; }
				}
				printf("(%d, %d, %d, %d, %d, %d), # %d+%d  best %d, %d\n", i + n * NUMCAND, ss1, sss1, ss2, sss2, s1+s2, s1, s2, best, bestidx);
				fflush(stdout);
			}
		}

	}

	cudaFree(grk_buf);
	cudaFree(device_result);
	cudaFree(ref);
	free(host_result);
*/

	return 0;
}

