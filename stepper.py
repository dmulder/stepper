#!/usr/bin/env python3

import difflib, sys, os.path, argparse
from dateutil.parser import parse as date_parse
import re, zmq, random

def similarity(a, b):
    return difflib.SequenceMatcher(None, a, b)

def discover(syslog, code_path):
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
    file_line_mo = re.compile(r'([\./\-\w]+):(\d+)')

    ln = 1
    with open(syslog, 'r') as f:
        buf_stamp = None
        buf = '' # Buffer for multi-line messages
        for line in f:
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
                continue
            date = date_parse(stamp)
            m = file_line_mo.match(line)
            if not m:
                sys.stderr.write('No filename found on line %d\n' % ln)
            filename = m.group(1)
            srcln = m.group(2)
            print(line)
            try:
                socket.send_string("%s:%s" % (os.path.abspath(os.path.join(code_path, filename)), srcln))
                socket.recv()
                input()
            except EOFError:
                socket.send_string('exit')
                socket.recv()
                socket.close()
                break
            ln += 1

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Stepper: Step through syslog output, opening the source code mentioned in the debug.", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("syslog", help="File where syslog messages are stored")
    parser.add_argument("code_path", help="Location of source code referenced in syslog messages")

    args = parser.parse_args()

    if not os.path.exists(args.syslog):
        sys.stderr.write('The specified syslog file "%s" does not exist\n' % args.syslog)
        exit(1)
    if not os.path.exists(args.code_path):
        sys.stderr.write('The specified code path does not exist\n' % args.code_path)
        exit(2)

    discover(args.syslog, args.code_path)

