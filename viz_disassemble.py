import argparse
import subprocess
import re
from collections import OrderedDict


parser = argparse.ArgumentParser(description='Reads an object file, disassembles it and generates a .dot graphviz file for visualization.')
parser.add_argument(dest="file", type=str, nargs=1, help='The input binary file.')
parser.add_argument('-m', '--method', dest="method", type=str, nargs=1, default='objdump', choices=["objdump", "gdb"], help='The method to use for disassembly')
parser.add_argument('-o', '--output', dest="output", type=str, nargs=1, help='The graphviz dot output file')
parser.add_argument('-a', '--assembly', dest="assembly", type=str, nargs=1, help='The Assembly Code collected from the Method.')

args = parser.parse_args()

def objdump(file_name):
    run_cmd = f"objdump -d {file_name} -C --no-show-raw-insn --visualize-jumps=off -w"
    output, error = subprocess.Popen(run_cmd.split(), stdout=subprocess.PIPE).communicate()

    output = output.decode('utf-8')
    if args.assembly:
        with open(args.assembly[0], "w") as f:
            f.write(output)

    output = output.split('Disassembly of section .text:')[1]

    funs = re.findall(r'\d+ <([a-zA-Z0-9_]+\([a-zA-Z0-9_]*\))>:', output)
    output = re.split(r'\d+ <[a-zA-Z0-9_]+\([a-zA-Z0-9_]*\)>:', output)[1:]

    all_funs = {}
    for f, o in zip(funs, output):
        f = f.strip()
        o = o.strip()
        all_funs[f] = []
        first = True
        sequential = False
        last_built_in_fn = None

        for line in o.split('\n'):
            line = ' '.join(line.strip().split())
            line = line.strip()
            if line == "": continue
            line_number, instr = line.split(':')
            line_number = line_number.strip()
            instr = instr.strip()
            if 'nopw' in instr or 'nopl' in instr:
                continue
            if first:
                all_funs[f].append({'data': OrderedDict(), 'next': []})
                all_funs[f][-1]['id'] = line_number
                first = False
                if sequential:
                    all_funs[f][-2]['next'].append((line_number, f))
                    sequential = False
                if last_built_in_fn:
                    all_funs[last_built_in_fn][-1]['next'].append((line_number, f))
                    last_built_in_fn = None

            all_funs[f][-1]['data'][line_number] = instr
            if 'call' in instr or 'jnz' in instr or 'jne' in instr or 'jmp' in instr:
                jmp_fn = instr.split()[2][1:]
                jmp_line = instr.split()[1]
                end = next((i for i, ch  in enumerate(jmp_fn) if ch in [">", "@", "+"]),None)
                if end:
                    jmp_fn = jmp_fn[:end]

                if jmp_fn not in funs:
                    if jmp_fn not in all_funs:
                        all_funs[jmp_fn] = [{'id': 0, 'next':[], 'data': {'stub1': 'stub1', 'stub2': 'stub2'}}]
                    all_funs[f][-1]['next'].append((0, jmp_fn))

                    last_built_in_fn = jmp_fn
                # elif jmp_fn in all_funs and jmp_line in list(itertools.chain(*[key for key in [list(dic.keys()) for dic in all_funs[jmp_fn]]])):
                elif jmp_fn in all_funs:
                    all_funs[f][-1]['next'].append((jmp_line, jmp_fn))
                
                first = True
                
                if 'call' not in instr and 'jmp' not in instr:
                    sequential = True



            
    dot_str = funcs_to_dot(all_funs)
    return dot_str


def to_html(output):
    output = str(output)
    output= output.replace('&', '&amp;')
    output= output.replace('<', '&lt;')
    output= output.replace('>', '&gt;')
    output= output.replace('"', '&quot;')
    return output

def funcs_to_dot(funcs):
    ret = 'digraph g {\n'

    for f_name, f_val in funcs.items():
        if 'stub1' not in f_val[0]['data']:
            label = f'''<<table border="0" cellspacing="0">
            <tr><td border="1" bgcolor="aquamarine">{to_html(f_name)}</td></tr>
            <tr><td border="1" bgcolor="lightsalmon">{to_html(list(f_val[0]['data'].keys())[0])}:   {to_html(f_val[0]['data'][list(f_val[0]['data'].keys())[0]])}</td></tr>
            <tr><td border="1" bgcolor="lightsalmon">{to_html(list(f_val[0]['data'].keys())[1])}:   {to_html(f_val[0]['data'][list(f_val[0]['data'].keys())[1]])}</td></tr>
            '''
        else:
            label = f'''<<table border="0" cellspacing="0">
            <tr><td border="1" bgcolor="aquamarine">{to_html(f_name)}</td></tr>
            '''
        for i, f_block in enumerate(f_val):
            for j, (ln, instr) in enumerate(f_block['data'].items()):
                if (i == 0 and j <= 1) or instr.startswith('stub'): continue
                label += f'\t<tr><td border="1">{to_html(ln)}:    {to_html(instr)}</td></tr>\n'
            label += '</table>>'
            ret += f'\t"{to_html(f_block["id"])}:{to_html(f_name)}" [shape=none, label={label}];\n'
            label = f'''<<table border="0" cellspacing="0">
            <tr><td border="1" bgcolor="aquamarine">{to_html(f_name)}</td></tr>'''

            

    for f_name, f_val in funcs.items():
        for f_block in f_val:

            for next_ln, next_fn in f_block['next']:
                ret += f'"{to_html(f_block["id"])}:{to_html(f_name)}" -> "{to_html(next_ln)}:{to_html(next_fn)}" [style=solid, color="black"];\n'
            


    ret += '}'
    return ret

if __name__ == "__main__":
    args = parser.parse_args()

    ret = objdump(args.file[0])
    if args.output:
        with open(args.output[0], 'w') as f:
            f.write(ret)
    