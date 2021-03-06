#!/usr/bin/env python3

import sys, os.path, argparse
from dateutil.parser import parse as date_parse
import re, zmq, random
import parse
import pathlib
from subprocess import Popen, PIPE
from shutil import which
import pexpect
import pickle
from tempfile import NamedTemporaryFile

__asts = {}
def get_ast(filename, code_path, funcname, use_fakes):
    global __asts

    if filename not in __asts:
        __asts[filename] = parse.parse_c(filename, code_path, use_fakes)
    return parse.lookup_function(__asts[filename], funcname)

def interact(filename, code_path, funcname, use_fakes):
    while True:
        command = input('> ').strip()
        if command == 'interact':
            print('Opening an interactive shell... type "exit" to leave the shell.')
            shell = pexpect.spawn(which('python3'))
            shell.sendline('import pickle, parse')
            shell.expect('>>> ')
            print('Parsing the c code...')
            ast = get_ast(filename, code_path, funcname, use_fakes)
            tmp = NamedTemporaryFile('wb', delete=False)
            pickle.dump(ast, tmp)
            shell.sendline('ast = pickle.load(open("%s", "rb"))' % tmp.name)
            shell.expect('>>> ')
            shell.interact()
            os.remove(tmp.name)
            tmp.close()
        elif command == '':
            break

def discover(syslog, code_path, use_fakes, line_num):
    debug_id = random.randint(5000, 6000)
    ui = os.path.join(os.path.dirname(sys.argv[0]), 'stepper_ui')
    if not os.path.exists(ui):
        ui = 'python3 %s' % os.path.join(os.path.dirname(sys.argv[0]), 'stepper_ui.py')
    rc = os.system('xterm -T "Syslog Stepper" -bg white -fg black -fn 9x15 -e %s %d 2>/dev/null &' % (ui, debug_id))
    if rc != 0:
        exit(rc)
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://127.0.0.1:%d" % debug_id)

    time_stamp_res = [re.compile('^\s*\[(\d+/\d+/\d+\s+\d+:\d+:[\d\.]+),\s+[^\]]+\]\s+(.*)$')]
    file_line_func_res = [re.compile(r'([\./\-\w]+):(\d+)\(([^\)]+)\)')]

    ln = 1
    with open(syslog, 'r') as f:
        buf_stamp = None
        buf = '' # Buffer for multi-line messages
        for line in f:
            if ln < line_num:
                ln += 1
                continue
            stamp = None
            for mo in time_stamp_res:
                m = mo.match(line)
                if m: # start a new line
                    stamp = buf_stamp
                    buf_stamp = m.group(1)
                    line = buf
                    buf = m.group(2) + '\n'
            if not stamp:
                buf += line
                ln += 1
                continue
            date = date_parse(stamp)
            filename = None
            srcln = None
            func = None
            for mo in file_line_func_res:
                m = mo.match(line)
                if m:
                    filename = m.group(1)
                    srcln = m.group(2)
                    func = m.group(3)
            filename = os.path.abspath(next(pathlib.Path(code_path).glob('**/%s' % filename)))
            print('%d: %s' % (ln, str(date)))
            print(line.strip())
            ln += 1
            if not filename or not srcln:
                sys.stderr.write('No filename found on line %d\n' % ln-1)
                continue
            try:
                socket.send_string("%s:%s" % (filename, srcln))
                socket.recv()
                interact(filename, code_path, func, use_fakes)
            except EOFError:
                print()
                socket.send_string('exit')
                socket.recv()
                socket.close()
                break

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Stepper: Step through syslog output, opening the source code mentioned in the debug.", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("syslog", help="File where syslog messages are stored")
    parser.add_argument("code_path", help="Location of source code referenced in syslog messages")
    parser.add_argument('--use-fakes', help="Use fake headers to parse source code", action="store_true", default=False)
    parser.add_argument('--line-num', help="The syslog line number to start at", action="store", default=1)

    args = parser.parse_args()

    if not os.path.exists(args.syslog):
        sys.stderr.write('The specified syslog file "%s" does not exist\n' % args.syslog)
        exit(1)
    if not os.path.exists(args.code_path):
        sys.stderr.write('The specified code path does not exist\n' % args.code_path)
        exit(2)

    discover(args.syslog, args.code_path, args.use_fakes, int(args.line_num))

