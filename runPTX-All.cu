#include <stdio.h>
#include <string>
#include <iostream>
#include <cstring>
#include <fstream>
#include <streambuf>
#include <cuda.h>
#include <cmath>
#include <vector>

#define IMPORTED_KERNEL


#ifndef IMPORTED_KERNEL

__global__ void memoryTest(long long * starting_address, long long * before1_load, long long * after1_load, long long * duration1, long long * before2_load, long long * after2_load, long long * duration2) {

    // long long int before1 = 0;
    // long long int after1 = 0;

    *before1_load = 0;
    *after1_load = 0;
    // *duration1 = 0;
    *before2_load = 0;
    *after2_load = 0;
    // *duration2 = 0;


    long long * start1 = starting_address;
    long long * start2 = starting_address;
    unsigned int i = 0;

    for (i = 0; i < 2047; i++) {
        starting_address[i] = (long long) &starting_address[i + 1];
    }

    i = 0;

    asm volatile("mov.u64 %0, %clock64 ;" : "=l"(*before1_load));
    // *before1_load = clock64();

    for (i = 0; i < 2048; i++) {
        start1 = (long long *) *start1;
    }

    asm volatile("mov.u64 %0, %clock64 ;" : "=l"(*after1_load));
    // *after1_load = clock64();
    
    asm volatile("mov.u64 %0, %clock64 ;" : "=l"(*before2_load));
    // *before2_load = clock64();

    for (i = 0; i < 2048; i++) {
        start2 = (long long *) *start2;
    }

    // asm volatile("mov.u64 %0, %clock64 ;" : "=l"(*after_load));
    asm volatile("mov.u64 %0, %clock64 ;" : "=l"(*after2_load));
    // *after2_load = clock64();

    *duration1 = *after1_load - *before1_load;
    *duration2 = *after2_load - *before2_load;
}
#endif


#ifdef IMPORTED_KERNEL
#define SAFE(X) if ((err = X) != CUDA_SUCCESS) printf("CUDA error %d at %d\n", (int)err, __LINE__)
#else
#define SAFE(x) if (0 != x) { abort(); }
#endif



#ifdef IMPORTED_KERNEL

CUdevice cuDevice;
CUcontext cuContext;
CUmodule cuModule;
CUfunction memoryTest;
CUresult err;

CUdeviceptr largeObjectArray;
CUdeviceptr * before;
CUdeviceptr * after;
CUdeviceptr * duration;

#else
long long * largeObjectArray;
long long * before1;
long long * after1;
long long * duration1;
long long * before2;
long long * after2;
long long * duration2;
#endif

int main(int argc, char * argv[]) {
    srand(time(NULL));
    
    int devID = 0;

    long long * _before;
    long long * _after;
    long long * _duration;

    cudaEvent_t start, stop;
    float milliseconds; 

    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    #ifdef IMPORTED_KERNEL
    SAFE(cuInit(0));
    SAFE(cuDeviceGet(&cuDevice, devID));

    SAFE(cuCtxCreate(&cuContext, 0, cuDevice));

    if (argc < 5) {
        printf("Usage: %s <num_requests> <cache_level> <memory_type> <ptx_filename>\n", argv[0]);
        printf("cache_level: L1, L2, BASE\n");
        printf("memory_type: CPU, GPU, UM\n");
        return 1;
    }

    int num_requests = atoi(argv[1]);
    char * cache_level = argv[2];
    char * memory_type = argv[3];
    char * ptx = argv[4];
  
    SAFE(cuModuleLoad(&cuModule, ptx));

    printf("Loaded module\n");

    char * fn_name = (char *) malloc(strlen("_Z10memoryTestPx") + (((num_requests * 3) + 1) * 2));

    snprintf(fn_name, strlen("_Z10memoryTestPx") + 1, "_Z10memoryTestPx");

    for (int i = 0; i < (num_requests * 3) + 1; i++) {
        snprintf(fn_name + strlen(fn_name), 3, "S_");
    }

    SAFE(cuModuleGetFunction(&memoryTest, cuModule, fn_name));

    printf("Got function\n");

    int region_size;
    int load_size;

    if (strcmp(cache_level, "L1") == 0) {
        region_size = 16384;
        load_size = 16384;
    } else if (strcmp(cache_level, "L2") == 0) {
        region_size = 786432;
        load_size = 786432;
    } else if (strcmp(cache_level, "BASE") == 0) {
        region_size = 6533595;
        load_size = 32768;
    } else {
        printf("Invalid region size\n");
        return 1;
    }

    if (strcmp(memory_type, "CPU") == 0) {
        SAFE(cuMemAllocHost((void **) &largeObjectArray, region_size * sizeof(long long)));
    } else if (strcmp(memory_type, "GPU") == 0) {
        SAFE(cuMemAlloc(&largeObjectArray, region_size * sizeof(long long)));
    } else if (strcmp(memory_type, "UM") == 0) {
        SAFE(cuMemAllocManaged(&largeObjectArray, region_size * sizeof(long long), CU_MEM_ATTACH_GLOBAL));
    } else {
        printf("Invalid memory type\n");
        return 1;
    }


    before = (CUdeviceptr *) malloc(sizeof(CUdeviceptr) * num_requests);
    after = (CUdeviceptr *) malloc(sizeof(CUdeviceptr) * num_requests);
    duration = (CUdeviceptr *) malloc(sizeof(CUdeviceptr) * num_requests);
    _before = (long long *) malloc(sizeof(long long) * num_requests);
    _after = (long long *) malloc(sizeof(long long) * num_requests);
    _duration = (long long *) malloc(sizeof(long long) * num_requests);

    for (int i = 0; i < num_requests; i++) {
        SAFE(cuMemAlloc(&before[i], sizeof(long long)));
        SAFE(cuMemAlloc(&after[i], sizeof(long long)));
        SAFE(cuMemAlloc(&duration[i], sizeof(long long)));
    }
    
    #else


    SAFE(cudaMalloc(&largeObjectArray, region_size * sizeof(long long)));
    
    
    SAFE(cudaMalloc(&before1, sizeof(long long)));
    SAFE(cudaMalloc(&after1, sizeof(long long)));
    SAFE(cudaMalloc(&duration1, sizeof(long long)));

    SAFE(cudaMalloc(&before2, sizeof(long long)));
    SAFE(cudaMalloc(&after2, sizeof(long long)));
    SAFE(cudaMalloc(&duration2, sizeof(long long)));
    #endif

    printf("Done allocations\n");

    printf("Memory Type: %s | Cache Level: %s\n", memory_type, cache_level);

    #ifdef IMPORTED_KERNEL

    void ** args = (void **) malloc(sizeof(void *) * (num_requests * 3) + 1);
    args[0] = &largeObjectArray;

    int k = 1;
    for (int i = 0; i < num_requests; i++) {
        args[k++] = &before[i];
        args[k++] = &after[i];
        args[k++] = &duration[i];
    }

    // cudaEventRecord(start);
    SAFE(cuLaunchKernel(memoryTest, 1, 1, 1, 1, 1, 1, 0, NULL, args, NULL));
    // cudaEventRecord(stop);
    // cudaEventSynchronize(stop);
    #else
    memoryTest<<<1,1>>>(largeObjectArray, before1, after1, duration1, before2, after2, duration2);
    #endif
    
    #ifdef IMPORTED_KERNEL
    SAFE(cuCtxSynchronize());
    #else
    SAFE(cudaDeviceSynchronize());
    #endif

    #ifdef IMPORTED_KERNEL
    for (int i = 0; i < num_requests; i++) {
        SAFE(cuMemcpyDtoH(&_before[i], before[i], sizeof(long long)));
        SAFE(cuMemcpyDtoH(&_after[i], after[i], sizeof(long long)));
        SAFE(cuMemcpyDtoH(&_duration[i], duration[i], sizeof(long long)));
    }

    milliseconds = 0;
    cudaEventElapsedTime(&milliseconds, start, stop);
    milliseconds *= 1e6;
    #else
    SAFE(cudaMemcpy(&_before1, before1, sizeof(int), cudaMemcpyDeviceToHost));
    SAFE(cudaMemcpy(&_after1, after1, sizeof(int), cudaMemcpyDeviceToHost));
    SAFE(cudaMemcpy(&_duration1, duration1, sizeof(int), cudaMemcpyDeviceToHost));
    SAFE(cudaMemcpy(&_before2, before2, sizeof(int), cudaMemcpyDeviceToHost));
    SAFE(cudaMemcpy(&_after2, after2, sizeof(int), cudaMemcpyDeviceToHost));
    SAFE(cudaMemcpy(&_duration2, duration2, sizeof(int), cudaMemcpyDeviceToHost));
    #endif

    for (int i = 0; i < num_requests; i++) {
        printf("Before %d: %lld\n", i, _before[i]);
        printf("After %d: %lld\n", i, _after[i]);
        printf("Duration %d: %lld\n", i, _duration[i]);
        printf("Per-Load Duration %d (/%d): %f\n", i, load_size, (double)_duration[i] / (double) load_size);
    }

    // printf("Kernel Duration: %f | %f\n", milliseconds, milliseconds / (float) load_size);


    #ifdef IMPORTED_KERNEL
    
    if (strcmp(memory_type, "CPU") == 0) {
        SAFE(cuMemFreeHost((void*) largeObjectArray));
    } else {
        SAFE(cuMemFree(largeObjectArray));
    }
    
    
    for (int i = 0; i < num_requests; i++) {
        SAFE(cuMemFree(before[i]));
        SAFE(cuMemFree(after[i]));
        SAFE(cuMemFree(duration[i]));
    }
    free(before);
    free(after);
    free(duration);

    free(_before);
    free(_after);
    free(_duration);

    free(args);
    #else
    SAFE(cudaFree(largeObjectArray));
    SAFE(cudaFree(before1));
    SAFE(cudaFree(after1));
    SAFE(cudaFree(duration1));

    SAFE(cudaFree(before2));
    SAFE(cudaFree(after2));
    SAFE(cudaFree(duration2));
    #endif

}