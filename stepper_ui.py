#!/usr/bin/env python3

# The MIT License (MIT)
# 
# Copyright (c) 2014 David Mulder
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import time, sys, os, os.path, zmq
from subprocess import Popen, PIPE

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://127.0.0.1:%s" % sys.argv[1])
filename = ''
previous_file = ''
line_num = None
proc = None
from glob import glob
import psutil

while True:
    mesg = socket.recv()
    socket.send(mesg)
    if mesg and proc:
        # Kill the process and the spawned child (proc + 1).
        try:
            children = [c.pid for c in proc.children()]
            for child in children:
                child.kill()
            proc.kill()
            proc = None
            sw_files = glob(os.path.join(os.path.dirname(previous_file.decode()), '.%s.*' % os.path.basename(previous_file.decode())))
            for sw in sw_files:
                os.remove(sw)
        except:
            pass
    if mesg == b'exit':
        break
    if mesg:
        filename, line_num = mesg.split(b':')
        proc = psutil.Process(Popen(['/bin/sh', '-c', 'vim +%s +"set cursorline" +"set so=999" %s' % (line_num.decode(), filename.decode())]).pid)
        previous_file = filename

socket.close()

