all: runPTX

runPTX:
	nvcc -o runPTX -Xptxas -O0 -Xcicc -O0 -Xcompiler -O0 -arch=sm_80 runPTX-All.cu -lcuda

clean:
	rm -rf runPTX