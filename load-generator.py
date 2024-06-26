import sys
import os
import subprocess

from itertools import product

def flatten_list(lst):
    flattened = []
    for item in lst:
        if isinstance(item, list):
            flattened.extend(flatten_list(item))
        else:
            flattened.append(item)
    return flattened

def flatten_to_tuples(lst, tuple_length):
    flattened = flatten_list(lst)
    tuples = []
    i = 0
    while i < len(flattened):
        tuples.append(tuple(flattened[i:i+tuple_length]))
        i += tuple_length
    return tuples

def write_file(filename, store_type, load_types, mem_region_size):  
    
    if not os.path.isdir(filename.split('/')[0]):
        os.mkdir(filename.split('/')[0])
    
    number_of_requests = len(load_types)
    number_of_sub_requests = len(load_types[0])
    
    print(f"req: {number_of_requests}\tsub_req: {number_of_sub_requests}\t{load_types}")
    
    num_param_reg = (3 * number_of_requests) + 1
    
    rd_counter = 0
    
    param_registers = list()
    load_registers = list()
    
    store_address = '%rd' + str(rd_counter)
    rd_counter += 1
    
    for i in range(number_of_requests):
        load_registers.append(dict())
        load_registers[i]['timer_start_dst'] = '%rd' + str(rd_counter)
        rd_counter += 1
        load_registers[i]['timer_end_dst'] = '%rd' + str(rd_counter)
        rd_counter += 1
        load_registers[i]['duration_dst'] = '%rd' + str(rd_counter)
        rd_counter += 1

    for i in range(number_of_requests):
        for j in range(number_of_sub_requests):
            if j not in load_registers[i]:
                load_registers[i][j] = dict()
            
            load_registers[i][j]['address'] = '%rd' + str(rd_counter)
            rd_counter += 1
        
        
    for i in range(number_of_requests):
        load_registers[i]['timer_start_src'] = '%rd' + str(rd_counter)
        rd_counter += 1
        load_registers[i]['timer_end_src'] = '%rd' + str(rd_counter)
        rd_counter += 1
        load_registers[i]['duration_src'] = '%rd' + str(rd_counter)
        rd_counter += 1
        load_registers[i]['consumer'] = '%rd' + str(rd_counter)
        rd_counter += 1
    
    for i in range(number_of_requests):
        for j in range(number_of_sub_requests):
            load_registers[i][j]['ld_reg_1'] = '%rd' + str(rd_counter) 
            rd_counter += 1
            
            load_registers[i][j]['ld_reg_2'] = '%rd' + str(rd_counter) 
            rd_counter += 1
            
            load_registers[i][j]['ld_reg_3'] = '%rd' + str(rd_counter) 
            rd_counter += 1
        
    param_registers.append(store_address)
    for i in range(number_of_requests):
        param_registers.append(load_registers[i]['timer_start_dst'])
        param_registers.append(load_registers[i]['timer_end_dst'])
        param_registers.append(load_registers[i]['duration_dst'])
    
    fn_string = f'_Z10memoryTestPx{"".join(["S_" for _ in range(len(param_registers))])}'
    
    with open(filename, 'w') as f:
        
        f.write('// Generated by load-generator.py\n\n')
        
        f.write('.version 7.7\n')
        f.write('.target sm_80\n')
        f.write('.address_size 64\n')
        f.write('.visible .entry ' + fn_string + '(\n')
        for i in range(num_param_reg):
            f.write('\t.param .u64 ' + fn_string + '_param_' + str(i))
            if i < num_param_reg - 1:
                f.write(',\n')
            else:
                f.write('\n')
        f.write(')\n{\n')
        f.write('\t.reg .pred\t%p<' + str(number_of_requests + 1) + '>;\n')
        f.write('\t.reg .b32\t%r<4>;\n')
        f.write('\t.reg .b64\t%rd<' + str(rd_counter) + '>;\n\n')
        
        for i, reg in enumerate(param_registers):
            f.write('\tld.param.u64\t' + param_registers[i] + ', [' + fn_string + '_param_' + str(i) + '];\n')
        
        f.write('\n')
        f.write('\tmov.u32\t%r1, 0;\n')
        
        for i in range(number_of_requests):
            for j in range(number_of_sub_requests):
                f.write(f'\tmov.u64\t{load_registers[i][j]["address"]}, {store_address};\n')
            
        f.write('\n')
        f.write('$Mem_store:\n')
        f.write(f'\t{store_type}.global.u64\t[{store_address}], {store_address}+8;\n')
        f.write(f'\t{store_type}.global.u64\t[{store_address}+8], {store_address}+16;\n')
        f.write(f'\t{store_type}.global.u64\t[{store_address}+16], {store_address}+24;\n')
        f.write(f'\t{store_type}.global.u64\t[{store_address}+24], {store_address}+32;\n')
        f.write(f'\tadd.u64\t{store_address}, {store_address}, 32;\n')
        f.write(f'\tadd.u32\t%r1, %r1, 32;\n')
        
        if mem_region_size == 'L1':
            f.write('\tsetp.lt.u32\t%p1, %r1, 131072;\n')
        elif mem_region_size == 'L2':
            f.write('\tsetp.lt.u32\t%p1, %r1, 6291456;\n')
        elif mem_region_size == 'BASE':            
            f.write('\tsetp.lt.u32\t%p1, %r1, 52268760;\n')
        
        f.write('\t@%p1 bra $Mem_store;\n')
        
        f.write('\n')
        
        for i in range(number_of_requests):
            f.write('\tmov.u32\t%r1, 0;\n\n')
            f.write(f'\tmov.u64\t{load_registers[i]["timer_start_src"]}, %clock64;\n\n')
            f.write(f'$Mem_load{i}:\n')
            
            for j in range(number_of_sub_requests):
                f.write(f'\t{load_types[i][j]}.global.u64\t{load_registers[i][j]["ld_reg_1"]}, [{load_registers[i][j]["address"]}];\n')
            
            for j in range(number_of_sub_requests):
                f.write(f'\t{load_types[i][j]}.global.u64\t{load_registers[i][j]["ld_reg_2"]}, [{load_registers[i][j]["ld_reg_1"]}];\n')
                
            for j in range(number_of_sub_requests):
                f.write(f'\t{load_types[i][j]}.global.u64\t{load_registers[i][j]["ld_reg_3"]}, [{load_registers[i][j]["ld_reg_2"]}];\n')
                
            for j in range(number_of_sub_requests):
                f.write(f'\t{load_types[i][j]}.global.u64\t{load_registers[i][j]["address"]}, [{load_registers[i][j]["ld_reg_3"]}];\n')    
            
            f.write(f'\tadd.u32\t%r1, %r1, 32;\n')
            
            for j in range(number_of_sub_requests):
                f.write(f'\tmov.u64\t{load_registers[i]["consumer"]}, {load_registers[i][j]["address"]};\n')
            
            if mem_region_size == 'L1':
                f.write('\tsetp.lt.u32\t%p1, %r1, 131072;\n')
            elif mem_region_size == 'L2':
                f.write('\tsetp.lt.u32\t%p1, %r1, 6291456;\n')
            elif mem_region_size == 'BASE':            
                f.write('\tsetp.lt.u32\t%p1, %r1, 262144;\n')
            
            
            f.write(f'\t@%p1 bra $Mem_load{i};\n')
            f.write('\n')
            f.write(f'\tmov.u64\t{load_registers[i]["timer_end_src"]}, %clock64;\n\n')
            
            
        for i in range(number_of_requests):
            f.write(f'\tst.global.u64\t[{load_registers[i]["timer_start_dst"]}], {load_registers[i]["timer_start_src"]};\n')
            f.write(f'\tst.global.u64\t[{load_registers[i]["timer_end_dst"]}], {load_registers[i]["timer_end_src"]};\n')
        
        f.write('\n')
        
        for i in range(number_of_requests):
            f.write(f'\tsub.u64\t{load_registers[i]["duration_src"]}, {load_registers[i]["timer_end_src"]}, {load_registers[i]["timer_start_src"]};\n')
    
        f.write('\n')
    
        for i in range(number_of_requests):
            f.write(f'\tst.global.u64\t[{load_registers[i]["duration_dst"]}], {load_registers[i]["duration_src"]};\n')
            
        f.write('\n')
        f.write('\tret;\n}')




if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python load-generator.py <number_of_load_requests>')
        sys.exit(1)

    number_of_requests = int(sys.argv[1])
    
    ST_TYPE = 'st'
    LD_TYPES = ['ld', 'ld.ca', 'ld.cg', 'ld.cv']
    LD_MEM_ORDER = ['ld.relaxed', 'ld.acquire']
    LD_SCOPES = ['.cta', '.gpu', '.sys']
    
    MEM_REGION_SIZES = ['L1', 'L2', 'BASE']
    
    LD_MEM_SCOPES = list()
    
    for ld_scope in LD_SCOPES:
        for ld_order in LD_MEM_ORDER:
            LD_MEM_SCOPES.append(ld_order + ld_scope)
    
    LD_MEM_SCOPES = list(set(LD_MEM_SCOPES))    
        
    all_tuples = list(product(LD_MEM_SCOPES, repeat=number_of_requests))
    
    for mem in MEM_REGION_SIZES:
        for tuple in all_tuples:
            _tuple = [[t] for t in tuple]
            filename = f'{number_of_requests}_loads_{mem}/{ST_TYPE}-{"-".join(tuple)}.ptx'
            write_file(filename, ST_TYPE, _tuple, mem)
            
            subprocess.run(['ptxas', '-Werror', '-arch=sm_80', filename, "-o", filename.replace('ptx', 'out'), '-O0'])
            
            sass_output = subprocess.run(['cuobjdump', '-sass', filename.replace('ptx', 'out')], capture_output=True)
            
            with open(filename.replace('ptx', 'sass'), 'w') as f:
                f.write(sass_output.stdout.decode('utf-8'))
        
        subprocess.run(['cp', 'runPTX', f'{number_of_requests}_loads_{mem}'])
        subprocess.run(['cp', 'run-all.sh', f'{number_of_requests}_loads_{mem}'])
                
    all_tuples = list(product(LD_TYPES, repeat=number_of_requests))
    
    for mem in MEM_REGION_SIZES:
        for tuple in all_tuples:
            
            _tuple = [[t] for t in tuple]
            
            filename = f'{number_of_requests}_loads_{mem}/{ST_TYPE}-{"-".join(tuple)}.ptx'
            write_file(filename, ST_TYPE, _tuple, mem)
            
            subprocess.run(['ptxas', '-Werror', '-arch=sm_80', filename, "-o", filename.replace('ptx', 'out'), '-O0'])
            
            sass_output = subprocess.run(['cuobjdump', '-sass', filename.replace('ptx', 'out')], capture_output=True)
            
            with open(filename.replace('ptx', 'sass'), 'w') as f:
                f.write(sass_output.stdout.decode('utf-8'))
        
        subprocess.run(['cp', 'runPTX', f'{number_of_requests}_loads_{mem}'])
        subprocess.run(['cp', 'run-all.sh', f'{number_of_requests}_loads_{mem}'])
        
    ld_types = sorted(LD_MEM_SCOPES).copy()
    
    ld_tuples = [ [ld1, ld2] for ld1 in ld_types for ld2 in ld_types ]
    
    for mem in MEM_REGION_SIZES:
        for tuple in ld_tuples:
            filename = f'1_loadmixed_{mem}/{ST_TYPE}-{"-".join(tuple)}.ptx'
            
            write_file(filename, ST_TYPE, [tuple], mem)
            
            subprocess.run(['ptxas', '-Werror', '-arch=sm_80', filename, "-o", filename.replace('ptx', 'out'), '-O0'])
            
            sass_output = subprocess.run(['cuobjdump', '-sass', filename.replace('ptx', 'out')], capture_output=True)
            
            with open(filename.replace('ptx', 'sass'), 'w') as f:
                f.write(sass_output.stdout.decode('utf-8'))
        
        subprocess.run(['cp', 'runPTX', f'1_loadmixed_{mem}'])
        subprocess.run(['cp', 'run-all.sh', f'1_loadmixed_{mem}'])