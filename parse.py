from pycparserext.ext_c_parser import GnuCParser as CParser
from pycparser.plyparser import ParseError
from subprocess import Popen, PIPE
from shutil import which
import re, os.path
import pathlib

__ignored_symbols = []

def __preprocess(filename, header_dir, opts=[]):
    opts.extend(['-D__alignof__(x)=', '-D__aligned__(x)=', '-D__attribute__(x)=', '-D__THROWNL=', '-D__signed__='])
    result = ''
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

def __guess_symbol(filename, linen, charn):
    global __ignored_symbols
    symbol = ''
    with open(filename, 'r') as r:
        buf = ''
        for i in range(linen-15):
            r.readline()
        for i in range(linen-15, linen-1):
            buf += r.readline()
        buf += r.readline()[:charn-1].rstrip()
        symbols = re.findall("'\\\\.?'|'.?'|\".+\"|\w+|\d+|-\d+|//|-=|\+=|\+\+|--|<<|>>|<=|>=|==|!=|&&|\|\||!|\"|\#|\$|%|&|\'|\(|\)|\*|\+|,|-|\.|/|:|;|<|=|>|\?|@|\[|\]|\\\\|\]|\^|_|`|\{|\||\}|~", buf)
        symbol = None
        for i in range(len(symbols)-1, -1, -1): # Pick the first identifier
            if re.match("[a-zA-Z0-9_]+", symbols[i]) and symbols[i] not in __ignored_symbols:
                symbol = symbols[i]
                break
    __ignored_symbols.append(symbol)
    if 'float' in symbol.lower():
        return '-D%s=float' % symbol
    else:
        raise

def parse_c(filename, header_dir):
    parse_error_mo = re.compile(r'([/\w\.\-]+):(\d+):(\d+): before: .*')
    ast = None
    retry_parse = True
    opts = []
    while retry_parse:
        source = __preprocess(filename, header_dir, opts)
        parser = CParser()
        try:
            ast = parser.parse(source, filename)
            retry_parse = False
        except ParseError as e:
            m = parse_error_mo.match(e.args[0])
            if not m:
                raise
            opt = __guess_symbol(m.group(1), int(m.group(2)), int(m.group(3)))
            if opt and opt not in opts:
                opts.append(opt)
            else:
                raise
    return ast

if __name__ == "__main__":
    import sys
    ast = parse_c(sys.argv[1], sys.argv[2])
    ast.show(showcoord=True)
