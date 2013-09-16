#!/usr/bin/env python
"""
 SlipStream Client
 =====
 Copyright (C) 2013 SixSq Sarl (sixsq.com)
 =====
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
 
      http://www.apache.org/licenses/LICENSE-2.0
 
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

import os
import sys
import shutil

def process(filename,cmd=None):
    ''' Append at the end of the file (e.g. rc.local) the SlipStream bootstrap
        file to trigger the execution of the node (e.g. package generation,
        image creation, deployment)
        Do the following:
           - Open target file
           - Reverse the lines
           - Process empty lines, if any
           - Look for exit or not empty line
                - If starts with exit, prepend the bootstrap line
                - If starts with none empty line (but not exit),
                  prepend the bootstrap script
           - Copy rest of lines
           - Move original file to <filename>.sav
           - Replace old file
        Option: The 'cmd' field can be used to customize the command that will be inserted in the file'''

    bootstrap = 'mkdir -p /tmp/slipstream/reports\n'
    if cmd == None:
        bootstrap += os.path.join(os.sep,'etc','slipstream.bootstrap.sh') \
                     + '  > ' + os.path.join(os.sep,'tmp','slipstream','reports','node-execution.log') \
                     + ' 2>&1 &\n'
    else:
        bootstrap += cmd + '\n'

    # Backup the file if it was not done before
    originalFilename = filename + '.orig'
    if not os.path.exists(originalFilename):
        shutil.copyfile(filename,originalFilename)
    
    file = open(filename)
    lines = file.readlines()
    newlines = []
    gotit = False
    lines.reverse()
    for line in lines:
        # Simply copy empty lines
        if gotit:
            newlines.append(line)
            continue
        if line.strip() == '':
            newlines.append(line)
            continue
        if line.strip().startswith('exit'):
            gotit = True
            newlines.append(line)
            newlines.append(bootstrap)
            continue
        gotit = True
        newlines.append(bootstrap)
        newlines.append(line)
    savedfilename = filename + '.sav'
    if os.path.exists(savedfilename):
        os.remove(savedfilename)
    shutil.move(filename, savedfilename)
    newfile = open(filename,'w')
    # reverse the lines
    newlines.reverse()
    newfile.writelines(newlines)
    newfile.close()
    os.chmod(filename, 0755)

if __name__ == '__main__':
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        sys.stderr.write('Error, usage is: %s <filename> [<command-string>], got: %s\n' % 
                         (sys.argv[0], ' '.join(sys.argv)))
        sys.exit(1)
    cmd = None
    if len(sys.argv) == 3:
        cmd = sys.argv[2]
    process(sys.argv[1],cmd)
    print 'Done!'
