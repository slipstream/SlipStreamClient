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

from slipstream.LocalRuntimeConnector import LocalRuntimeConnector

import os
import sys
import time
import getopt
import socket
import urllib2
import CommandBase
from slipstream import RestClient
from slipstream import LocalRuntimeConnector   


class MainProgram(CommandBase.CommandBase):
    ''' Ping the SlipStream server.'''
    
    USAGE = '''\
Usage: %(progName)s [<username> <password>] <slipstream-url>

<slipstream-url> SlipStream url (e.g. https://slipstream.sixsq.com.
<username>       Valid SlipStream standard username.  By default extract
                 username from local environment.
<password>       Corresponding SlipStream password.  By default extract
                 username from local environment.

options:
  --sms          Send SMS when ping fails.
  --quiet        Only prints minimum information.
  --verbose      Prints additional information (default).
  -h, --help     Show this message.
'''
    def __init__(self, argv=None):
        self.url = None
        self.username = None
        self.password = None
        self.withSms = False
        self.statusFilename = RestClient.RestClient.pingStatusFile
        self.errorFilename = RestClient.RestClient.pingErrorFile
        self.timeout = 30*60 # 30 minutes
        super(MainProgram,self).__init__(argv)
        return

    def parseArgs(self, argv):
        try:
            options, args = getopt.getopt(argv[1:], 'hd:',
                                          ['sms','help','quiet','timeout=',
                                           'verbose','help'])
        except getopt.GetoptError, err:
            msg=err.__str__()
            self.usageExit(msg)
        for opt, value in options:
            if opt in ('--sms',):
                self.withSms = True
            if opt in ('--quiet',):
                self.quiet = True
            if opt in ('--verbose',):
                self.verbose = True
            if opt in ('--timeout',):
                self.timeout = value
        if len(args) < 1:
            self.usageExitTooFewArguments()
        if len(args) > 3:
            self.usageExitTooManyArguments()
        if len(args) == 1:
            self.url = args[0]
        if len(args) == 3:
            self.url = args[2]
        if len(args) > 1:
            self.username = args[0]
            self.password = args[1]
        return

    def doWork(self):
        # If the username and password are not passed as arguments, assume we're
        # in a cloud context, if not, use the LocalRuntimeConnector such that 
        # client doesn't try to retrieve user-data from the cloud instance
        cloudConnectorModules = {}
        if self.username and self.password:
            LocalRuntimeConnector.LocalRuntimeConnector.instanceDataDict = {'server':self.url}
            cloudConnectorModules = {'runtime':'slipstream.LocalRuntimeConnector'}
        client = RestClient.RestClient(self.verbose,cloudConnectorModules)
        print >> sys.stderr, 'Pinging the SlipStream server at address:', self.url
        statusOk = 'OK'
        statusError = 'Error'
        error = None
        try:
            client.ping(self.username,self.password)
            status = statusOk
        except Exception, ex:
            status = statusError
            error = str(ex)
            print >> sys.stderr, 'Error:', error
        if not os.path.exists(self.statusFilename):
            handle = open(self.statusFilename,'w')
            handle.write(statusOk)
            handle.close()
            oldStatus = statusOk
        else:
            handle = open(self.statusFilename)
            oldStatus = handle.read().strip()
            handle.close()
        if status != oldStatus:
            handle = open(self.statusFilename,'w')
            handle.write(status)
            handle.close()
            hostname = socket.gethostname()
            if status != statusError:
                msg = 'SlipStream server at address %s is back to normal.' % client.serverUrl
            else:
                msg = 'SlipStream server at address %s failed with error %s.' % (client.serverUrl,error)
                open(self.errorFilename,'w').write(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()) + ': ' + error)
            msg += ' Test executed on host: %s' % hostname
            if self.withSms:
                print >> sys.stderr, 'Sending SMS to inform of the status change: %s' % msg
                h = urllib2.urlopen('http://www.chrus.ch/mysms/http/send.php?user=41774468119&pwd=smSstatuS2009&from=41774468119&to=41774468119,33677907238&msg=%s' % msg.replace(' ','+'))
        if error:
            sys.exit(-1)
        return

main = MainProgram

##############################################################################
# Executing this module from the command line
##############################################################################

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
