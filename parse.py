from pycparser import c_parser as __c_parser
from subprocess import Popen, PIPE
from shutil import which
import re, os.path
import pathlib

def preprocess(filename, header_dir):
    result = ''
    opts = []
    ret = -1
    while ret != 0:
        cmd = [which('cpp'), filename]
        cmd.extend(opts)
        p = Popen(cmd, stderr=PIPE, stdout=PIPE)
        out = p.communicate()
        err = out[-1].decode()
        ret = p.returncode
        if ret == 0:
            result = out[0].decode()
            break
        headers = re.findall(r'fatal error: ([/\w\.]+): No such file or directory', err)
        filepath = pathlib.Path(os.path.dirname(filename))
        for header in headers:
            includes = pathlib.Path(header_dir).glob('**/%s' % header)
            best_rank = 0
            best_choice = ''
            for include in includes:
                rank = 0
                for i in range(len(include.parts)):
                    if include.parts[i] == filepath.parts[i]:
                        rank += 1
                    else:
                        break
                if rank > best_rank:
                    best_rank = rank
                    best_choice = str(include)
            if len(best_choice) == 0:
                print('%s not found in header directory %s' % (header, header_dir))
                exit(1)
            opts.append('-I%s' % best_choice.replace(header, ''))
        if len(headers) == 0 and ret != 0:
            print(err)
            exit(1)
    return result

def parse_c(filename, header_dir):
    source = preprocess(filename, header_dir)
    parser = __c_parser.CParser()
    ast = parser.parse(source, filename)
    ast.show(showcoord=True)

if __name__ == "__main__":
    import sys
    parse_c(sys.argv[1], sys.argv[2])
