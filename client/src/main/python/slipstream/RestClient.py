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

import ConfigParser
import httplib
import os
import sys
import tarfile
import time
import subprocess

import httplib2

import slipstream.exceptions.Exceptions as Exceptions
import util


try:
    import xml.etree.ElementTree as ET
except ImportError:
    # In Python 2.4, ElementTree was in a different package
    import elementtree.ElementTree as ET
import socket
from time import strftime

svnurl = "$HeadURL: https://code.sixsq.com/svn/SlipStream/trunk/SlipStreamClient/src/main/python/slipstream/RestClient.py $"


def getVersion():
    """ Extract the version from the SVN tag.  If the code was extracted from
        trunk, return the current local date, if the code was extracted from
        a tag, return the tag, otherwise return 'unknown'. """
    version = 'unknown'
    if '/slipstream/trunk/' in svnurl:
        version = strftime(util.timeformat)
    elif '/slipstream/tag/' in svnurl:
        version = svnurl.split('/slipstream/tag/')[-1]
    return version


class RestClient:
    """ During a deployment execution, we distinguish between 3 cases:
        1- Nominal execution, and no abortion triggered by other nodes
        2- Failure in a target, which sets the current node in fail mode
        3- Nominal execution, but with the abort flag raised following
           a failure by another node.
        The isAbort field tracks the abort status of the entire execution,
        the isFailure field track the local failure of the target execution.
        <p/>
        Node state is tracked via two key/value pairs
        <p/>
        The connector mechanism is in place to abstract the cloud environment:
        1- compute (e.g. EC2): API to start, stop and query vms
        2- storage (e.g. S3): API to upload and download data to and from
           storage
        3- runtime (e.g. EC2): API to interact with the cloud environment from
           within a running vm.
        The connectors are loaded dynamically by name and are static.
        <p/>
        Credentials for performing actions uses username/password normally
        passed to the client via the vm instance data.  For testing purposes
        and to run the client in standalone mode, this behaviour can be changed
        by using a special runtime connector.
        """
    tmpdir = os.path.join(os.sep, 'tmp', 'slipstream')
    reportsdir = os.path.join(tmpdir, 'reports')
    volumeIdFile = os.path.join(tmpdir, 'volumeId')
    pingStatusFile = os.path.join(tmpdir, 'ping.status')
    pingErrorFile = os.path.join(tmpdir, 'ping.error')
    localDiidFile = os.path.join(tmpdir, 'diid')

    # Execution instance property namespace and separator
    globalNamespaceName = 'ss'
    NODE_PROPERTY_SEPARATOR = ':'
    globalNamespacePrefix = globalNamespaceName + NODE_PROPERTY_SEPARATOR

    # Node multiplicity index separator - e.g. <nodename>.<index>:<prop>
    nodeMultiplicityIndexSeparator = '.'
    nodeMultiplicityStartIndex = '1'

    # Counter names
    initCounterName = globalNamespacePrefix + 'initCounter'
    finalizeCounterName = globalNamespacePrefix + 'finalizeCounter'
    terminateCounterName = globalNamespacePrefix + 'terminateCounter'

    # Orchestrator name
    orchestratorName = 'orchestrator'

    # Name given to the machine being built for node state
    defaultMachineName = 'machine'
    defaultMachineNamePrefix = defaultMachineName + NODE_PROPERTY_SEPARATOR

    # List of reserved and special node names
    reservedNodeNames = [globalNamespaceName, orchestratorName, defaultMachineName]

    # State names
    STATE_KEY = 'state'
    stateMessagePropertyName = 'statemessage'

    urlIgnoreAbortAttributeFragment = '?ignoreabort=true'

    SLIPSTREAM_DIID_ENV_NAME = 'SLIPSTREAM_DIID'

    def __init__(self, verbose=False, cloudConnectorModules={}):
        """ cloudConnectorModules contain the Python modules to use to connect to the cloud.
            Recognised keys are:
               - 'computing' (e.g. EC2)
               - 'storage' (e.g. S3) """

        self.verbose = verbose

        self.userParameters = None
        self.diid = None

        # Service URLs
        self.serverUrl = None
        self.runServiceUrl = None
        self.navigatorServiceUrl = None
        self.authnServiceUrl = None
        self.authzServiceUrl = None

        self.credentials = None
        self.instantiatedImages = []
        self.images = None
        self.password = None
        self.isAuthenticated = False
        self.isAbort = False
        self.isFailure = False

        self.nodeName = None

        # Load configuration parameters from cloud environment and file
        parser = self._loadConfigFile()

        # Load cloud connectors
        self.computingCloudConnectorModule = None
        self.runtimeCloudConnectorModule = None
        self.storageCloudConnectorModule = None

        self._loadConnectors(parser, cloudConnectorModules)

        self._configureServiceEndpoints(parser)

        self.state = None
        self.refQName = None

        if os.path.exists(os.path.join(self.tmpdir, 'cookie')):
            self.cookie = open(os.path.join(self.tmpdir, 'cookie')).read()
        else:
            self.cookie = None

        self.bashScriptErrorHandlingFragment = 'error=$?\n'
        self.bashScriptErrorHandlingFragment += 'if [ $error != 0 ]; then\n'
        self.bashScriptErrorHandlingFragment += '    exit $error\n'
        self.bashScriptErrorHandlingFragment += 'fi\n'

        certPemFile = 'cert.pem'
        self.certPemFileLocation = os.path.join(self.tmpdir, certPemFile)
        keyPemFile = 'key.pem'
        self.keyPemFileLocation = os.path.join(self.tmpdir, keyPemFile)

    def reset(self):
        url = self.runServiceUrl + self.getDiid()
        self._httpPost(url, 'reset', 'text/plain')

    def _authenticate(self, username=None, password=None):
        """ Authenticate with the server.  Use the username/password passed as
            input parameters, otherwise use the ones provided by the instance
            cloud context. """
        if not username and not password:
            try:
                username = self.getInstanceData('username')
                password = self.getInstanceData('password')
            except KeyError as ex:
                raise Exceptions.ClientError("Missing parameter: " + str(ex))

        body = 'username=' + username + '&password=' + password + '&login=Username'
        resp, _ = self._httpCall(self.authnServiceUrl + 'login', 'POST', body, contentType='text/plain', retry=False)
        self.cookie = resp['set-cookie']

        return self.cookie

    def _buildRemoteImage(self, timeout, ebsPreRecipeScript=None,
                          createinstance=False, strictversion=False):
        """ Execute scripts remotely on a remote instance. Used during disk and machine image creation.
            If the installClient flag is True, also install the client in the target image.
            If the createinstance flag is True, instantiate a new image"""

        slipStreamLocation = os.path.join(os.sep, 'opt', 'slipstream')
        slipStreamClientLocation = os.path.join(slipStreamLocation, 'client')
        slipStreamScriptRoot = os.path.join(slipStreamClientLocation, 'scripts')

        # Setup the EC2 environment
        self._setupEnvironment()

        # Retrieve the image
        refQName = self._getModuleReference()

        # if strictversion False, retreive the module name, from the qname such that we
        # use the latest version
        if not strictversion:
            refQName = self._getModule(refQName)

        details = self._getImageDetails(refQName, withResolver=True)

        # Check image id
        if 'imageId' not in details or details['imageId'] is None:
            msg = 'Missing image id.  Can\'t build an image without a reference image id as a starting point. '
            msg += 'Make sure that your module your module references ends with a module having a valid image id (recommended), '
            msg += 'or provide your module with a valid image id (less recommended since not reproducible).'
            raise Exceptions.ClientError(msg)

        # We need the credentials, so we retrieve the instance data dictionary, which also contains the user data (i.e. EC2 user-data)
        userDataDict = self.getInstanceData()
        userData = self._createUserDataString(self.getDiid(), self.serverUrl,
                                              userDataDict['username'],
                                              userDataDict['password'],
                                              userDataDict['version.category'],
                                              userDataDict['clienturl'],
                                              imageShortName=RestClient.defaultMachineName)

        self.assignDefaultAwsSecurityGroupNameIfNotDefined()
        credentials = self._getUserCredentials(validate=True)

        instanceIdFile = os.path.join(self.tmpdir, 'instanceid')
        if createinstance:
            self._printSectionHead('Instantiating reference image: %s' % details['imageId'])
            instanceId = self._instentiateImage(details['imageId'], userData, credentials)
            open(instanceIdFile, 'w').write(instanceId)
        else:
            try:
                instanceId = open(instanceIdFile).read().strip()
                self._printSectionHead('Reusing instantiated image')
            except IOError:
                raise Exceptions.ClientError(
                    'Missing file %s, have you forgotten to run the command without --createinstance before?' % instanceIdFile)

        self.setInfoSys(RestClient.defaultMachineNamePrefix + 'instanceid', instanceId)
        print >> sys.stderr, 'Remote instance is:', instanceId
        # Wait for the image to boot
        hasBooted = False
        timer = 0
        info = None
        while not hasBooted:
        # Check if the reference image is ready
            info = self._getImageInstanceInfo(instanceId)
            status = info['status']
            if status == 'running':
                break
                # Sleep
            if timeout != 0 and timer >= timeout:
                raise Exceptions.TimeoutException("Exceeded timeout limit while waiting for reference image to boot")

            print >> sys.stderr, "    waiting for instance %s to boot, currently: %s" % (instanceId, status)
            sys.stdout.flush()
            sleepTime = 5
            time.sleep(sleepTime)
            timer += sleepTime
            # Publish instance details

        print >> sys.stderr, 'Boot completed.\n'
        self.setNodeStatusRunning(self.defaultMachineName)

        self.setInfoSys(RestClient.defaultMachineNamePrefix + 'dnsName', info['dnsName'])
        self.setInfoSys(RestClient.defaultMachineNamePrefix + 'privateDnsName', info['privateDnsName'])

        # Save locally the keypair file
        # We already validated the existence of the keys, we now need to check their value
        if not credentials['AWS_gsg-keypair_Name']:
            raise ValueError("Invalid parameter: AWS_gsg-keypair_Name, got '%s'" % credentials['AWS_gsg-keypair_Name'])
        keypairFilename = os.path.join(self.tmpdir, credentials['AWS_gsg-keypair_Name'])

        fd = os.open(keypairFilename, os.O_CREAT | os.O_WRONLY, 0600)
        if not credentials['AWS_gsg-keypair']:
            raise ValueError("Invalid parameter: AWS_gsg-keypair, got '%s'" % credentials['AWS_gsg-keypair'])
        os.write(fd, credentials['AWS_gsg-keypair'])
        os.close(fd)

        # Save locally the cert PEM file
        fd = os.open(self.certPemFileLocation, os.O_CREAT | os.O_WRONLY, 0600)
        os.write(fd, credentials['AWS_Certificate_Pem'])
        os.close(fd)

        # Save locally the key PEM file
        fd = os.open(self.keyPemFileLocation, os.O_CREAT | os.O_WRONLY, 0600)
        os.write(fd, credentials['AWS_Private_Key_Pem'])
        os.close(fd)

        print >> sys.stderr, 'Checking connection to instance'
        cmd = 'ssh -i ' + keypairFilename + ' root@' + info['dnsName'] + ' date'
        self._executeRemoteCommand(cmd)
        print >> sys.stderr, 'Connection OK.'

        #
        # PreRecipe
        #

        # prerecipe script
        # Copy pre-recipe script, if it exists
        if 'prerecipe' in details:
            self._printSectionHead('Pre-Recipe')

            preRecipeFilename = 'prerecipe'
            preRecipeFilenameSource = os.path.join(self.reportsdir, preRecipeFilename)
            preRecipeFilenameTarget = preRecipeFilename

            recipe = open(preRecipeFilenameSource, 'w')
            recipe.writelines(details['prerecipe'] + '\n')
            recipe.close()
            os.chmod(preRecipeFilenameSource, 0755)

            print >> sys.stderr, 'Copying prerecipe script to target instance'
            cmd = 'scp -B -i ' + keypairFilename + ' ' + preRecipeFilenameSource + ' root@' + info['dnsName'] \
                  + ':' + preRecipeFilenameTarget
            self._systemCall(cmd, False)

            cmd = 'ssh -i ' + keypairFilename + ' root@' + info['dnsName'] + ' ./' + preRecipeFilenameTarget
            print >> sys.stderr, 'Calling prerecipe script:', cmd
            self._systemCall(cmd, False)
            print >> sys.stderr, '\nDone prerecipe.\n'
        else:
            print >> sys.stderr, ('No prerecipe to execute.\n')

        # Retrieve the Python interpreter location if defined in a property, otherwise
        # use the system default
        # Checking if a config file must be created and copied over (used to set python environment)
        pythonInterpreterLocation = 'python'
        customPythonConfigFilenameTarget = None
        if 'properties' in details and 'slipstream.python.location' in details['properties']:
            print >> sys.stderr, 'Setting-up the custom Python environment'
            pythonInterpreterLocation = details['properties']['slipstream.python.location']

            customPythonConfigFilename = 'slipstream.custom.env.conf'
            customPythonConfigFilenameSource = os.path.join(self.tmpdir, customPythonConfigFilename)
            open(customPythonConfigFilenameSource, 'w').write('''
if [ -z $PATH ]; then
    PATH="%(pythonBinLocation)s"
else
    PATH="%(pythonBinLocation)s:$PATH"
fi
export PATH
''' % {'pythonBinLocation': os.path.dirname(pythonInterpreterLocation)})

            customPythonConfigFilenameTarget = os.path.join(self.tmpdir, customPythonConfigFilename)
            print >> sys.stderr, 'Creating tmp directory: %s' % self.tmpdir
            cmd = 'ssh -i ' + keypairFilename + ' root@' + info['dnsName'] + ' "' \
                  + pythonInterpreterLocation + ' -c \\\"import os; os.makedirs(\'' \
                  + self.tmpdir + '\') if not os.path.exists(\'' + self.tmpdir + '\') else None\\\""'
            self._systemCall(cmd, False)

            print >> sys.stderr, 'Copying custom environment configuration file: %s to target instance' % customPythonConfigFilename
            cmd = 'scp -B -i ' + keypairFilename + ' ' + customPythonConfigFilenameSource + ' root@' + info['dnsName'] \
                  + ':' + customPythonConfigFilenameTarget
            self._systemCall(cmd, False)

            print >> sys.stderr, 'Done setting-up the Python environment'
        else:
            print >> sys.stderr, 'Using standard Python installation.'

        #
        # Remote script generation
        #

        # Generate script to be executed remotely
        self._printSectionHead('Remote scripts generation')
        remoteScriptFilename = 'slipstream-remote-script'
        remoteScriptFilenameSource = os.path.join(self.reportsdir, remoteScriptFilename)
        remoteScriptFilenameTarget = os.path.join(self.tmpdir, remoteScriptFilename)
        script = open(remoteScriptFilenameSource, 'w')
        script.writelines('#!/bin/bash\n')

        # slipStreamScriptLocationient environment
        script.writelines('echo "Sourcing the environment for the SlipStream command-line client"\n')
        script.writelines('source ' + os.path.join(slipStreamScriptRoot, 'slipstream.orchestrator.setup\n'))

        # Check if we need to source the custom python environment
        if customPythonConfigFilenameTarget:
            script.writelines('echo "Sourcing the custom python environment configuration file"\n')
            script.writelines('source ' + customPythonConfigFilenameTarget + '\n')

            # Packages
            # FIXME: extract this and put it in something like an os family thing
        #        script.writelines('# Setting environment variable: DEBIAN_FRONTEND=noninteractive to allow headless package installation\n')
        #        script.writelines('export DEBIAN_FRONTEND=noninteractive\n')

        packageInstallCmd = 'ss-install-package '

        if 'packages' in details:
            script.writelines('# Calling package manager for package(s) to install\n')
            script.writelines(packageInstallCmd + ' ' + ' '.join(details['packages']) + '\n')
            script.writelines(self.bashScriptErrorHandlingFragment)
        else:
            script.writelines('echo no user package to install\n')

        # Script for EBS volume creation
        ebsPreRecipeFilename = 'disk-image-script'
        ebsPreRecipeFilenameSource = os.path.join(self.reportsdir, ebsPreRecipeFilename)
        ebsPreRecipeFilenameTarget = os.path.join(self.tmpdir, ebsPreRecipeFilename)

        if (ebsPreRecipeScript):
            recipe = open(ebsPreRecipeFilenameSource, 'w')
            recipe.writelines(ebsPreRecipeScript + '\n')
            recipe.close()
            os.chmod(ebsPreRecipeFilenameSource, 0755)
            script.writelines('# Calling pre-recipe script\n')
            script.writelines('%s\n' % ebsPreRecipeFilenameTarget)
            script.writelines(self.bashScriptErrorHandlingFragment)
        else:
            script.writelines('echo no disk image script to execute\n')

        # recipe script
        recipeFilename = 'recipe'
        recipeFilenameSource = os.path.join(self.reportsdir, recipeFilename)
        recipeFilenameTarget = os.path.join(self.tmpdir, recipeFilename)

        if 'recipe' in details:
            recipe = open(recipeFilenameSource, 'w')
            recipe.writelines(details['recipe'] + '\n')
            recipe.close()
            os.chmod(recipeFilenameSource, 0755)
            script.writelines('# Calling custom script\n')
            script.writelines('%s\n' % recipeFilenameTarget)
            script.writelines(self.bashScriptErrorHandlingFragment)
        else:
            script.writelines('echo no recipe to execute\n')

        script.close()
        os.chmod(remoteScriptFilenameSource, 0755)
        print >> sys.stderr, '\n\nGenerated remote script:'
        print >> sys.stderr, 'START>>>\n'
        print >> sys.stderr, ''.join(open(remoteScriptFilenameSource).readlines())
        print >> sys.stderr, '\n<<<END\n\n'

        #
        # Installation
        #

        # Copy scripts into the instance

        # First mkdir
        self._printSectionHead('Image creation')
        print >> sys.stderr, 'Making remote tmp directory to host the scripts'
        cmd = 'ssh -i ' + keypairFilename + ' root@' + info['dnsName'] + ' mkdir -p /tmp/slipstream'
        self._systemCall(cmd, False)

        scriptDirname = os.path.join(os.sep, 'opt', 'slipstream', 'client', 'scripts')
        nodeExecutionBootstrap = 'slipstream.bootstrap.sh'
        nodeExecutionBootstrapSource = os.path.join(scriptDirname, nodeExecutionBootstrap)
        bootstrapTargetDir = os.path.join(os.sep, 'etc')
        nodeExecutionBootstrapTarget = os.path.join(bootstrapTargetDir, nodeExecutionBootstrap)
        print >> sys.stderr, 'Copying node execution bootstrap file: %s to target instance' % nodeExecutionBootstrap
        cmd = 'scp -B -i ' + keypairFilename + ' ' + nodeExecutionBootstrapSource + ' root@' + info['dnsName'] \
              + ':' + nodeExecutionBootstrapTarget
        self._systemCall(cmd, False)

        print >> sys.stderr, 'Copying remote script: %s to target instance' % remoteScriptFilename
        cmd = 'scp -B -i ' + keypairFilename + ' ' + remoteScriptFilenameSource + ' root@' + info['dnsName'] \
              + ':' + remoteScriptFilenameTarget
        self._systemCall(cmd, False)

        # Copy ebs script, if it exists
        if os.path.exists(ebsPreRecipeFilenameSource):
            print >> sys.stderr, 'Copying disk image script: %s to target instance' % ebsPreRecipeFilename
            cmd = 'scp -B -i ' + keypairFilename + ' ' + ebsPreRecipeFilenameSource + ' root@' + info['dnsName'] \
                  + ':' + ebsPreRecipeFilenameTarget
            self._systemCall(cmd, False)

        # Copy recipe script, if it exists
        if os.path.exists(recipeFilenameSource):
            print >> sys.stderr, 'Copying recipe script: %s to target instance' % recipeFilename
            cmd = 'scp -B -i ' + keypairFilename + ' ' + recipeFilenameSource + ' root@' + info['dnsName'] \
                  + ':' + recipeFilenameTarget
            self._systemCall(cmd, False)

        print >> sys.stderr, 'Copying cert PEM file: %s to target instance' % os.path.basename(self.certPemFileLocation)
        cmd = 'scp -B -i ' + keypairFilename + ' ' + self.certPemFileLocation + ' root@' + info['dnsName'] \
              + ':' + self.certPemFileLocation
        self._systemCall(cmd, False)

        print >> sys.stderr, 'Copying key PEM file: %s to target instance' % os.path.basename(self.keyPemFileLocation)
        cmd = 'scp -B -i ' + keypairFilename + ' ' + self.keyPemFileLocation + ' root@' + info['dnsName'] \
              + ':' + self.keyPemFileLocation
        self._systemCall(cmd, False)

        # Install SlipStream client on remote machine (needed to create volumes and snapshots)
        print >> sys.stderr, 'Pushing SlipStream client into image'
        print >> sys.stderr, 'Creating target directory'
        cmd = 'ssh -i ' + keypairFilename + ' root@' + info['dnsName'] \
              + ' mkdir -p /opt/slipstream/client'
        self._systemCall(cmd, False)

        print >> sys.stderr, 'Copying the client tarball'
        tarballName = 'slipstream-client.tgz'
        tarballPath = os.path.join(slipStreamClientLocation, tarballName)
        cmd = 'scp -B -i ' + keypairFilename + ' ' + tarballPath + ' root@' + info['dnsName'] \
              + ':/opt/slipstream/client'
        self._systemCall(cmd, False)

        print >> sys.stderr, 'Inflating the tarball'
        cmd = pythonInterpreterLocation + ' -c \\\"import os;import tarfile;os.chdir(\'%s\');tar = tarfile.open(\'%s\',\'r:gz\');[tar.extract(tarinfo) for tarinfo in tar]\\\"' % (
            slipStreamClientLocation, tarballPath)
        cmd = 'ssh -i ' + keypairFilename + ' root@' + info['dnsName'] \
              + ' "' + cmd + '"'
        print >> sys.stderr, 'Calling:', cmd
        self._systemCall(cmd, False)

        # ssh into the image and start the upgrade
        print >> sys.stderr, 'Executing the remote script via ssh'

        cmd = 'ssh -i ' + keypairFilename + ' root@' + info['dnsName'] + ' ' + remoteScriptFilenameTarget
        print >> sys.stderr, 'Calling:', cmd
        self._systemCall(cmd, False)

        return credentials, info

    def _createBucket(self, bucketname, retry=True):
        """ Create a single bucket.  Retry once if the creation failed """
        try:
            credentials = self._getUserCredentials()
            response = self.storageCloudConnectorModule.getConnector(credentials[AmazonCredentialsPlugin.AWS_Access_Id],
                                                                     credentials[
                                                                         AmazonCredentialsPlugin.AWS_Secret_Key]). \
                create_bucket(bucketname.lower(), headers={'Content-Type': 'text/plain'})
            if response.http_response.status == 201 or response.http_response.status == 200:
                return
            raise ValueError('Error creating S3 bucket.  Error code: %s with reason: %s' % (
                response.http_response.status, response.message))
        except:
            if retry:
                return self._createBucket(bucketname, False)
            raise

    def _createExecution(self, refqname):
        """ Launch a new execution """

        self.refQName = refqname

        url = self.runServiceUrl
        diid = self._httpPost(url, 'refqname=' + refqname, 'text/plain')

        # Update the local DIID
        self.setLocalDiid(diid)

        return diid

    def _createUserDataString(self, diid, serverUrl, username, password, category, clientUrl, imageShortName=None,
                              parameters={}):
        """ FIXME: replace these params with a dict"""
        # Don't put spaces around the '=' sign such that the file can be sourced
        # in bash (for example)
        _parameters = {'diid': diid,
                       'username': username,
                       'password': password,
                       'version.category': category,
                       'clienturl': clientUrl,
                       'server': serverUrl}
        # Update the list with the input parameters, which will overwrite the
        # default list, hence avoiding any duplicates
        _parameters.update(parameters)
        userData = ''
        if imageShortName:
            _parameters['imagename'] = imageShortName

        for param in _parameters:
            if _parameters[param]:
                userData += param + '=' + _parameters[param] + '\n'
        return userData

    def _executeRemoteCommand(self, cmd):
        """ Perform a system call, and retry until it succeeds or the timeout is reached.
            This is useful for calls that are expected to fail for network reasons, but
            can hide problem if the command is doomed!"""
        timer = 0
        sleepTime = 5
        timeout = 300

        # Try a few times, since the instance might not be totally ready
        try:
            self._systemCall(cmd)
        except Exceptions.ClientError:
            while True:
                # Sleep
                if timeout != 0 and timer >= timeout:
                    raise Exceptions.TimeoutException("Exceeded timeout limit while waiting for command to succeed.\n" +
                                                      "   Commands was: %s" % cmd)
                sys.stdout.flush()
                sleepTime = 5
                time.sleep(sleepTime)
                timer += sleepTime
                print >> sys.stderr, '    Retrying failed command: %s' % cmd
                try:
                    self._systemCall(cmd)
                    break
                except Exceptions.ClientError:
                    pass
        return

    def _getCategory(self):
        return self.runtimeCloudConnectorModule.getConnector().getInstanceData('version.category')

    def _getUserCredentials(self, validate=True, validateAll=False):
        """ Extract user credentials, inlcuding keys like:
                AWS_Access_Id
                AWS_Secret_Key
                AWS_gsg-keypair_Name
                AWS_gsg-keypair
                AWS_Security_Group_Name
                AWS_Certificate_Pem
                AWS_Private_Key_Pem
                AWS_Account_Number
            And optionally validate all the credentials.  If validateAll is
            false, only validate the essential keys"""
        essentialKeys = [AmazonCredentialsPlugin.AWS_Access_Id,
                         AmazonCredentialsPlugin.AWS_Secret_Key]
        optionalKeys = ['AWS_gsg-keypair_Name',
                        'AWS_gsg-keypair',
                        'AWS_Security_Group_Name',
                        'AWS_Certificate_Pem',
                        'AWS_Private_Key_Pem',
                        'AWS_Account_Number']
        if not self.credentials:
            # Populate the credentials
            paramDict = {}

            #            # Check that the client is authenticated, or that at least the
            #            # username is set (by the authenticate method)
            #            if not self.isAuthenticated:
            #                raise Exceptions.ClientError('Client not authenticated, did you call authenticate()?')

            xuser = self._httpGet(self.authzServiceUrl + 'users/' + self.getInstanceData('username'))
            root = ET.fromstring(xuser.encode('utf-8'))
            parameters = root.findall('parameters/parameter')
            for parameter in parameters:
                value = parameter.text
                if not value:
                    value = ''
                name = parameter.get('name')
                paramDict[name] = value
            self.credentials = paramDict

            # Check if what we need to validate
            keys = essentialKeys
            if validateAll:
                keys.extend(optionalKeys)
            for key in keys:
                if key not in self.credentials:
                    raise Exceptions.ClientError("Missing EC2 credential '%s'" % key)
                if self.credentials[key] is None:
                    raise Exceptions.ClientError(
                        "Wrong value for EC2 credential '%s', got '%s'" % (key, self.credentials[key]))
        return self.credentials

    def _getImages(self):
        """Returns a dict of {imageShortName:imageQname} for each image in the
           deployment version"""

        if self.images:
            return self.images

        url = self.serverUrl + '/' + self._getModuleReference()
        content = self._httpGet(url)
        root = ET.fromstring(content)
        nodes = root.find('nodes')
        images = {}
        if nodes:
            entries = nodes.findall('entry')
            for e in entries:
                # Pull the parameters and check if multiplicity is set
                multiplicity = 1
                for parameter in e.findall('node/properties/entry/parameter'):
                    if parameter.get('name') == 'multiplicity':
                        multiplicity = int(parameter.text)
                        break
                imageShortName = e.findtext('string')
                imageQname = e.find('node').get('name')

                for i in range(1, multiplicity + 1):
                    images[imageShortName + RestClient.nodeMultiplicityIndexSeparator + str(i)] = imageQname

        self.images = images
        return self.images

    def _getDeploymentPostProcessingScript(self):
        """Return the post processing script. Returns None if none is defined."""
        url = self.navigatorServiceUrl + self._getModuleReference()
        content = self._httpGet(url)
        root = ET.fromstring(content)
        #imageType = root.get('imageType')
        params = root.findall('parameters/parameter')
        script = None
        for p in params:
            if p.get('name') == 'post-processing':
                script = p.text
                break
        return script

    def _getImageInstanceInfo(self, instanceId, credentials=None):
        """ Return the EC2 instance info for a single instanceId """
        return self._getImagesInstanceInfo([instanceId])[instanceId]

    def _getImagesInstanceInfo(self, instanceIds):
        """ Return the EC2 instance info for instanceIds """

        credentials = self._getUserCredentials()

        response = self.computingCloudConnectorModule.getConnector(credentials[AmazonCredentialsPlugin.AWS_Access_Id],
                                                                   credentials[
                                                                       AmazonCredentialsPlugin.AWS_Secret_Key]).describe_instances(
            instanceIds)
        if response.is_error:
            raise Exceptions.ServerError('Failed retrieving image description from EC2 for images: %s with reason: %s' % (
                instanceIds, str(response)))
        if self.verbose:
            print response.parse()
        instances = {}
        for line in response.parse():
            if 'INSTANCE' in line:
                info = {}
                info['instanceId'] = line[1]
                info['imageId'] = line[2]
                info['dnsName'] = line[3]
                info['privateDnsName'] = line[4]
                info['status'] = line[5]
                info['zone'] = line[11]
                instances[info['instanceId']] = info
        return instances

    def _getInfoSys(self, key, ignoreAbort=False):
        # These special keys offer a translation between EC2 instance data and SlipStream data
        specialKeys = {'nodename': 'imagename'}
        if key in specialKeys:
            return self.getInstanceData()[specialKeys[key]]
        url = self.runServiceUrl + self.getDiid() + '/' + key
        if ignoreAbort:
            url += RestClient.urlIgnoreAbortAttributeFragment
        content = self._httpGet(url, accept='text/plain')

        return self._stripValue(content)

    def _stripValue(self, value):
        return value.strip().strip('"').strip("'")

    def _getLocalDiid(self):
        if os.path.exists(self.tmpdir):
            return open(RestClient.localDiidFile).read().strip()
        else:
            return None

    def _getModule(self, qname):
        return qname.split('/versions')[0]

    def _getModuleReference(self):
        if not self.refQName:
            url = self.runServiceUrl + self.getDiid()
            content = self._httpGet(url)
            root = ET.fromstring(content)
            refQName = root.get('moduleResourceUrl')
            self.refQName = refQName
        return self.refQName

    def _getImageDetails(self, imageqname, withResolver=False, withVirtualResolver=False):
        """ Return the details of the buildable module (i.e. image or blockStore):
            e.g. imageType, imageId.
            If withResolver is True (used for building images), resolve the
            image id from its module reference (if set).
            If withVirtualResolver is True (used for deployment execution),
            resolve the image id from its module reference, but return the
            referenced image id if the module is virtual.
            If not, simply fill the dictionary with the metadata from the
            imageqname without processing the referenced module."""
        url = self.navigatorServiceUrl + imageqname
        if withResolver:
            url += "?resolve=true"
        elif withVirtualResolver:
            url += "?resolvevirtual=true"
        content = self._httpGet(url)
        root = ET.fromstring(content)

        # Extract all the module's attributes
        details = {}
        for key in root.keys():
            details[key] = root.get(key)

        packagesNode = root.findall('packages/string')
        if packagesNode:
            packages = []
            for package in packagesNode:
                packages.append(package.text)
            details['packages'] = packages

        if root.findtext('prerecipe'):
            details['prerecipe'] = root.findtext('prerecipe')

        if root.findtext('recipe'):
            details['recipe'] = root.findtext('recipe')

        propertyNodes = root.findall('parameters/parameter')
        if propertyNodes:
            properties = {}
            for property in propertyNodes:
                properties[property.get('name')] = property.text
            details['properties'] = properties

        parameterNodes = root.findall('outputParameters/parameter')
        if parameterNodes:
            parameters = {}
            for parameter in parameterNodes:
                parameters[parameter.get('name')] = parameter.text
            details['outputParameters'] = parameters

        parameterNodes = root.findall('inputParameters/parameter')
        if parameterNodes:
            parameters = {}
            for parameter in parameterNodes:
                parameters[parameter.get('name')] = parameter.text
            details['inputParameters'] = parameters

        authzNode = root.findall('authz')
        if authzNode:
            permissions = ('ownerGet', 'ownerPut', 'ownerDelete', 'ownerPost',
                           'groupGet', 'groupPut', 'groupDelete', 'groupPost',
                           'publicGet', 'publicPut', 'publicDelete', 'publicPost')
            acls = []
            for permission in permissions:
                if authzNode[0].get(permission) and authzNode[0].get(permission) == 'true':
                    acls.append(permission)
            details['authz'] = acls

        return details

    def _httpGet(self, url, accept='application/xml'):
        return self.httpCall(url, 'GET', accept=accept)

    def _httpPut(self, url, body=None, contentType='application/xml', accept='application/xml'):
        return self.httpCall(url, 'PUT', body, contentType, accept)

    def _httpPost(self, url, body=None, contentType='application/xml'):
        return self.httpCall(url, 'POST', body, contentType)

    def _httpDelete(self, url):
        self.httpCall(url, 'DELETE')
        return

    def _httpCall(self, url, method, body=None, contentType='application/xml', accept='application/xml', retry=True):
        h = httplib2.Http(".cache")
        h.force_exception_to_status_code = False
        if self.verbose:
            print 'Contacting the server with %s, at: %s' % (method, url)
        headers = {}
        if contentType:
            headers['Content-Type'] = contentType
        if accept:
            headers['Accept'] = accept
        if self.cookie:
            headers['cookie'] = self.cookie
            if self.verbose:
                print 'Adding cookie to header:', self.cookie
        else:
            if self.verbose:
                print 'No cookie found'
        try:
            if len(headers):
                resp, content = h.request(url, method, body, headers=headers)
            else:
                resp, content = h.request(url, method, body)
        except httplib.BadStatusLine:
            raise Exceptions.NetworkError('Error: BadStatusLine contacting: ' + url)
        if self.verbose:
            print 'Received response:\n', resp
            print 'with content:\n' + unicode(content, 'latin-1')
        if not str(resp.status).startswith('2'):
            if str(resp.status).startswith('3'):
                if resp.status == 302:
                    # Redirected
                    resp, content = self.httpCall(resp['location'], method, body, accept)
                else:
                    raise Exception('Should have been handled by httplib2!! ' + str(resp.status) + ": " + resp.reason)
            if str(resp.status).startswith('4'):
                if resp.status == 409:
                    if 'Abort flag' in resp.reason:
                        self.isAbort = True
                        raise Exceptions.AbortException(resp.reason[resp.reason.index('Abort flag'):])
                    else:
                        raise Exceptions.NotYetSetError(resp.reason)
                if retry:
                    # FIXME: fix the server such that 406 is not returned when cookie expires
                    if resp.status == 401 or resp.status == 406:
                        self._authenticate()
                        return self._httpCall(url, method, body, contentType, accept, False)
                if self.verbose:
                    msg = 'Failed calling method %s on url %s, with reason: %s' % \
                          (method, url, str(resp.status) + ": " + resp.reason)
                else:
                    msg = resp.reason
                if resp.status == 404:
                    clientEx = Exceptions.NotFoundError(msg)
                else:
                    clientEx = Exceptions.ClientError(msg)
                clientEx.code = resp.status
                raise clientEx
            if str(resp.status).startswith('5'):
                if retry:
                    return self._httpCall(url, method, body, contentType, accept, False)
                raise Exceptions.ServerError('Failed calling method %s on url %s, with reason: %s' %
                                             (method, url, str(resp.status) + ": " + resp.reason))
            # If the content is a unicode string, convert it explicitely
        try:
            content = unicode(content, 'utf-8')
        except:
            # If it fails (e.g. it's not a string-like media-type) ignore it
            pass
        return resp, content

    def _instentiateImage(self, imageId, userData, credentials):
        """ Instantiate a new image, passing it the userData (i.e. EC2 user-data) and with the right credentials """
        response = self.computingCloudConnectorModule. \
            getConnector(credentials[AmazonCredentialsPlugin.AWS_Access_Id],
                         credentials[AmazonCredentialsPlugin.AWS_Secret_Key]). \
            run_instances(imageId, minCount=1, maxCount=1,
                          keyName=credentials['AWS_gsg-keypair_Name'],
                          groupIds=([credentials['AWS_Security_Group_Name']]),
                          userData=userData)
        if response.is_error:
            raise Exceptions.ServerError('Failed instantiating image %s with reason: %s' % (imageId, str(response)))

        if self.verbose:
            print response.parse()

        # Retrieve the instance info:
        #     ["INSTANCE", instanceId, imageId, dnsName, privateDnsName, instanceState]
        instanceId = None
        for line in response.parse():
            if 'INSTANCE' in line:
                instanceId = line[1]
                break
        self.instantiatedImages.append(instanceId)
        return instanceId

    def _isValidCategory(self, category):
        if category == 'Package':
            return True
        if category == 'Machine Image':
            return True
        if category == 'Disk Image':
            return True
        if category == 'Deployment':
            return True
        if category == 'Project':
            return True
        else:
            return False

    def _loadConfigFile(self):
        """ Read properties from configuration file and overwrite the values
            from cloud instance metadata. """
        parser = ConfigParser.ConfigParser()
        filename = util.getConfigFileName()
        parser.read(filename)

        return parser

    def _configureServiceEndpoints(self, parser):
        """ The result is used to configure the end-point for the different services """
        server = parser.get('System', 'server')

        # Code below assumes that the server values does NOT have a trailing slash.
        # Make sure that all of them are removed.  This should be made more robust in
        # the future.
        server = server.rstrip('/')
        #        print 'server (before):', server

        # Override local settings from user data (e.g. passed to EC2 during instantiation)
        try:
            server = self.getInstanceData('server')
        except KeyError:
            pass

        # Assemble end-point fields
        self.serverUrl = server
        self.runServiceUrl = self.serverUrl + '/run/'
        self.navigatorServiceUrl = self.serverUrl + '/module/'
        self.authnServiceUrl = self.serverUrl + '/'
        self.authzServiceUrl = self.serverUrl + '/'

    def _loadConnectors(self, parser, connectors={}):
        """ Load connector from info in the config file, unless passed as parameter. """

        computingConnectorName = parser.get('System', 'computingconnector')
        runtimeConnectorName = parser.get('System', 'runtimeconnector')
        storageConnectorName = parser.get('System', 'storageconnector')
        if 'computing' in connectors:
            computingConnectorName = connectors['computing']
        if 'runtime' in connectors:
            runtimeConnectorName = connectors['runtime']
        if 'storage' in connectors:
            storageConnectorName = connectors['storage']

        self.computingCloudConnectorModule = self._loadModule(computingConnectorName)
        self.runtimeCloudConnectorModule = self._loadModule(runtimeConnectorName)
        self.storageCloudConnectorModule = self._loadModule(storageConnectorName)

    def _loadModule(self, moduleName):
        # Load the modules
        namespace = ''
        name = moduleName
        if name.find('.') != -1:
            # There's a namespace so we take it into account
            namespace = '.'.join(name.split('.')[:-1])

        return __import__(name, fromlist=namespace)

    def _printSectionHead(self, message):
        if not message:
            message = ''
        noofdashes = 4
        separation = (2 * noofdashes + 2 + len(message)) * '='
        before = '\n\n' + separation
        after = separation
        print >> sys.stderr, before
        print >> sys.stderr, noofdashes * '=', message, noofdashes * '='
        print >> sys.stderr, after

    def _qualifyKey(self, key):
        """Qualify the key, if not already done, with the right nodename"""

        _key = key

        # Is this a reserved or special nodename?
        for reserved in RestClient.reservedNodeNames:
            if _key.startswith(reserved + RestClient.NODE_PROPERTY_SEPARATOR):
                return _key

        # Is the key namespaced (i.e. contains node/key separator: ':')?
        if RestClient.NODE_PROPERTY_SEPARATOR in _key:
            # Is the nodename in the form: <nodename>.<index>?  If not, make it so
            # such that <nodename>:<property> -> <nodename>.1:<property
            bits = _key.split(RestClient.NODE_PROPERTY_SEPARATOR)
            nodenamePart = bits[0]
            propertyPart = bits[1]  # safe since we've done the test in the if above
            bits = nodenamePart.split(RestClient.nodeMultiplicityIndexSeparator)
            nodename = bits[0]
            if len(bits) == 1:
                _key = nodename + \
                    RestClient.nodeMultiplicityIndexSeparator + \
                    RestClient.nodeMultiplicityStartIndex + \
                    RestClient.NODE_PROPERTY_SEPARATOR + \
                    propertyPart
            return _key

        # Are we in the context of a deployment?
        category = self._getCategory()

        if category == 'Deployment':
            # If we're in the context of a deployment, prepend the nodename
            # to the key
            try:
                _key = self.getNodeName() + RestClient.NODE_PROPERTY_SEPARATOR + _key
            except KeyError:
                # The Orchestrator is probably making this call
                _key = RestClient.orchestratorName + RestClient.NODE_PROPERTY_SEPARATOR + _key

        else:
            # Otherwise we're in the context of a machine or disk image creation
            try:
                _key = self.getNodeName() + RestClient.NODE_PROPERTY_SEPARATOR + _key
            except KeyError:
                # The Orchestrator is probably making this call
                _key = RestClient.orchestratorName + RestClient.NODE_PROPERTY_SEPARATOR + _key

        return _key

    def _setDiid(self, diid):
        """ Saves the diid to a local file and return the file path """
        self.diid = diid
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir)
        diidFilePath = os.path.join(self.tmpdir, 'diid')
        open(diidFilePath, 'w').write(diid)
        return diidFilePath

    def _setNodeStatus(self, statemsg, failure=False, final=False, active=False, nodename=None):
        """ Set the node state and statemessage.
            the state can go through the following transitions:
            1- inactive -> active -> done
            2- inactive -> active -> failing -> failed
            and corresponding to the execution state of the node.
            <p/>
            The statemsg gives a more verbose human message on the state of the
            node.
            <p/>
            failure indicates that the state should be set to failure, while
            final indicates that the state should be put in a final state,
            taking into account whether the transiant state is nominal
            or not. """
        # in the case we're building an image or a disk, we need to know if the
        # state and message should be set on the orchestrator or the node being built.
        # For this, the nodename argument is used
        stateMessagePropertyName = self.stateMessagePropertyName
        statePropertyName = self.STATE_KEY
        if nodename:
            stateMessagePropertyName = nodename + RestClient.NODE_PROPERTY_SEPARATOR + self.stateMessagePropertyName
            statePropertyName = nodename + RestClient.NODE_PROPERTY_SEPARATOR + self.STATE_KEY
        self.setInfoSys(stateMessagePropertyName, statemsg, ignoreAbort=True)

        # Set the state of the node
        if active:
            if self.isFailure:
                self.setInfoSys(statePropertyName, 'failing', ignoreAbort=True)
            else:
                self.setInfoSys(statePropertyName, 'active', ignoreAbort=True)
        if failure:
            self.isFailure = True
            self.setInfoSys(statePropertyName, 'failing', ignoreAbort=True)
        if final:
            if self.isFailure:
                self.setInfoSys(statePropertyName, 'failed', ignoreAbort=True)
            else:
                self.setInfoSys(statePropertyName, 'done', ignoreAbort=True)
        return

    def _setS3AclPublic(self, bucket, key, connector):
        """ Get the acl for bucket/key object, and add make it publicly readable """

        res = connector.get_acl(bucket, key)
        data = res.object.data
        root = ET.fromstring(data)
        aclList = root.find('{http://s3.amazonaws.com/doc/2006-03-01/}AccessControlList')
        grant = ET.SubElement(aclList, 'Grant')
        grantee = ET.SubElement(grant, 'Grantee')
        grantee.set('{http://www.w3.org/2001/XMLSchema-instance}type', 'Group')
        uri = ET.SubElement(grantee, 'URI')
        uri.text = 'http://acs.amazonaws.com/groups/global/AllUsers'
        permission = ET.SubElement(grant, 'Permission')
        permission.text = 'READ'
        str = ET.tostring(root)

        res = connector.put_acl(bucket, key, str)

        if res.http_response.status != 200:
            raise Exceptions.ClientError(res.http_response.reason, res.http_response.status)
        return res

    def _setState(self, state):
        self.state = state
        self.setInfoSys(RestClient.globalNamespacePrefix + RestClient.STATE_KEY, state, ignoreAbort=True)
        return

    def _setupCredentials(self):
        # if the credentials are not already locally stored, retrieve them and store them
        if not os.path.exists(self.certPemFileLocation) or not os.path.exists(self.keyPemFileLocation):
            credentials = self._getUserCredentials()

            # Save locally the cert PEM file
            fd = os.open(self.certPemFileLocation, os.O_CREAT | os.O_WRONLY, 0600)
            os.write(fd, credentials['AWS_Certificate_Pem'])
            os.close(fd)

            # Save locally the key PEM file
            fd = os.open(self.keyPemFileLocation, os.O_CREAT | os.O_WRONLY, 0600)
            os.write(fd, credentials['AWS_Private_Key_Pem'])
            os.close(fd)
        return

    def _setupEnvironment(self):
        EC2_HOME = os.path.join(os.sep, 'opt', 'ec2-api-tools')
        PATH = os.path.join(EC2_HOME, 'bin')
        JAVA_HOME = os.path.join(os.sep, 'usr')
        if 'PATH' in os.environ:
            os.environ['PATH'] = PATH + os.path.pathsep + os.environ['PATH']
        else:
            os.environ['PATH'] = PATH
        if 'JAVA_HOME' not in os.environ:
            os.environ['JAVA_HOME'] = JAVA_HOME
        if 'EC2_HOME' not in os.environ:
            os.environ['EC2_HOME'] = EC2_HOME
        return

    def _systemCall(self, cmd, retry=True):
        """ Execute system call and return stdout.  Raise an exception if the command fails"""
        if self.verbose:
            print 'Command:', cmd
        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
        (child_stdin, child_stdout) = (p.stdin, p.stdout)
        child_stdin = child_stdin
        stdout = []
        while True:
            out = child_stdout.readlines(1)
            if not out:
                break
            stdout.extend(out)
            sys.stdout.writelines(out)
        returnCode = p.wait()
        if returnCode:
            if retry:
                return self._systemCall(cmd, False)
            else:
                raise Exceptions.ClientError("Error executing command '%s', with error code: %s" % (cmd, returnCode))
        return stdout

    def _updateImage(self, imageqname, attributes):
        """Update the image with the given attributes.
        If an attribute starts with 'parameters--', 'inputParameters--' or 'outputParameters--',
        the attribute is placed in the corresponding parameters element, instead of
        an xml attribute of the root element.
        """
        url = self.navigatorServiceUrl + imageqname
        xml = self._httpGet(url)
        root = ET.fromstring(xml)
        parametersMask = 'parameters--'
        for attribute in attributes:
            if parametersMask in attribute.lower():
                # strip the start of the attributes to insert it in the right parameters set
                parametersNodeName = attribute.split('--')[0]
                # Strip
                paramName = attribute.split('--')[1]
                paramNode = None  # node of the attribute
                for node in root.findall(parametersNodeName + '/parameter'):
                    if node.get('name') == paramName:
                        paramNode = node
                        break
                if paramNode is None:
                    paramsNode = root.find(parametersNodeName)
                    if not paramsNode:
                        paramsNode = ET.SubElement(root, parametersNodeName)
                    paramNode = ET.SubElement(paramsNode, 'parameter')
                    paramNode.set('name', paramName)
                paramNode.text = attributes[attribute]

            else:
                # simple attribute
                root.set(attribute, attributes[attribute])

        xml = ET.tostring(root)
        self._httpPut(url, xml)
        return

    def _uploadReport(self, report, retry=True):
        nodeName = self.getNodeName()
        body = open(report).read()
        # Check if the repository already exists
        url = self.serverUrl + '/repository/' + self.getDiid() + '/'
        try:
            self._httpGet(url, accept="*/*")
        except Exceptions.ClientError, ex:
            if ex.code == 404:
                # Doesn't exists, create it
                self._httpPut(url, nodeName, 'text/plain', accept="*/*")
            else:
                raise
            # There's a bug in the Restlet redirection, where the redirection is not returned
        # so we don't use the redirected url, but the real one: /repository/...
        # Upload the file
        url += os.path.basename(report)
        self._httpPut(url, body, 'application/x-gtar', 'text/uri-list; charset=ISO-8859-1')
        return

    def abortInfoSys(self, reason=None, cancel=False, nodename=None):
        """ Set the abort flag for both the global execution and the
            node speficif flag."""
        abort = 'abort'
        globalAbort = RestClient.globalNamespacePrefix + abort

        # Clear the flag if cancel
        if cancel:
            url = self.runServiceUrl + self.getDiid() + '/' + globalAbort + RestClient.urlIgnoreAbortAttributeFragment
            self._httpDelete(url)
            self.isAbort = False
            return

        if not reason:
            reason = 'true'
            # Set the global flag
        self.setInfoSys(globalAbort, reason, ignoreAbort=True)
        # Set the node specific flag
        abortStr = abort
        if nodename:
            abortStr = nodename + RestClient.NODE_PROPERTY_SEPARATOR + abort
        self.setInfoSys(abortStr, reason, ignoreAbort=True)

        # Set the class flag
        self.isAbort = True

        return

    def attacheVolume(self, volumeId, mountDir, deviceName, createCopy,
                      timeout, fileSystemType='ext3', formatDisk=False):
        """ Attach a volume to a local directory, via a device.  If createCopy is True,
            create a copy (via a snapshot) of the volume.  If the volumeId starts with
            'snap-' consider it as a snapshot and skip the snapshot creation process """
        self._setupCredentials()

        instanceId = self.getInstanceData('instanceId')

        snapshotId = None
        if volumeId.startswith('snap-'):
            snapshotId = volumeId

        info = self._getImageInstanceInfo(instanceId)
        zone = info['zone']
        if createCopy and not snapshotId:
            print >> sys.stderr, "Creating a copy of the volume: %s" % volumeId
            cmd = 'ec2-create-snapshot -K %s -C %s %s' % (self.keyPemFileLocation,
                                                          self.certPemFileLocation,
                                                          volumeId)
            res = self._systemCall(cmd)
            for line in res:
                if 'SNAPSHOT' in line:
                    snapshotId = line.split()[1]
                    gotit = True
                    break
            if not gotit:
                raise Exceptions.VolumeError('Error calling: %s, the command didn\'t respond as expected')

            # Read the new snapshot id and wait for its creation to be completed
            print >> sys.stderr, "Waiting for snapshot to be created"
            cmd = 'ec2-describe-snapshots -K %s -C %s %s' % (self.keyPemFileLocation,
                                                             self.certPemFileLocation,
                                                             snapshotId)
            timer = 0
            sleepTime = 5
            gotit = False
            status = 'Unknown'
            while True:
                res = self._systemCall(cmd)
                for line in res:
                    if 'SNAPSHOT' in line:
                        status = line.split()[3]
                        if status == 'completed':
                            gotit = True
                        break
                if (timeout != 0 and timer >= timeout):
                    raise Exceptions.TimeoutException("Exceeded timeout limit (waiting for: %s" % cmd)
                if gotit:
                    print >> sys.stderr, "    Snapshot created: %s" % snapshotId
                    break
                print >> sys.stderr, "    Waiting for %s" % status
                sys.stdout.flush()
                time.sleep(sleepTime)
                timer += sleepTime

        if snapshotId:
            volumeId = self.createVolume(None, zone, timeout, snapshotId)
            print >> sys.stderr, "New volume: %s created from the snapshot: %s" % (volumeId, snapshotId)

        cmd = 'ec2-attach-volume -K %s -C %s -i %s -d %s %s' % (self.keyPemFileLocation,
                                                                self.certPemFileLocation,
                                                                instanceId, deviceName, volumeId)
        print >> sys.stderr, "Attaching volume: %s to device: %s on instance: %s" % (volumeId, deviceName, instanceId)

        try:
            self._systemCall(cmd)
        except Exceptions.ClientError, ex:
            raise Exceptions.VolumeError(str(ex))

        print >> sys.stderr, "    Waiting for volume to be attached"
        cmd = 'ec2-describe-volumes -K %s -C %s %s' % (self.keyPemFileLocation,
                                                       self.certPemFileLocation,
                                                       volumeId)
        # Wait for the volume to be created
        timer = 0
        sleepTime = 5
        gotit = False
        status = 'Unknown'
        while True:
            try:
                res = self._systemCall(cmd)
            except Exceptions.ClientError, ex:
                raise Exceptions.VolumeError(str(ex))
            for line in res:
                if 'ATTACHMENT' in line:
                    status = line.split()[4]
                    if status == 'attached':
                        gotit = True
                    break
            if (timeout != 0 and timer >= timeout):
                raise Exceptions.TimeoutException("Exceeded timeout limit (waiting for: %s" % cmd)
            if gotit:
                break
            print >> sys.stderr, "    Waiting for %s" % status
            sys.stdout.flush()
            time.sleep(sleepTime)
            timer += sleepTime

        if formatDisk:
            print >> sys.stderr, "    Formating the device: %s with type: %s" % (deviceName, fileSystemType)
            cmd = 'yes | mkfs -t %s %s' % (fileSystemType, deviceName)
            self._systemCall(cmd)

        if not os.path.exists(mountDir):
            os.makedirs(mountDir)
        cmd = 'mount %s %s' % (deviceName, mountDir)
        self._systemCall(cmd)

        return volumeId

    def authenticate(self, username=None, password=None):
        return self._authenticate(username, password)

    def buildBlockStore(self, createinstance, strictversion, timeout):
        """ Build the data store, by instantiating the reference image, and then executing the recipe script  """

        blockDir = {
            'fileSystemType': 'ext3',
            'deviceName': '/dev/sdh',
            'mountDir': '/mnt/data-store',
            'size': '50',
            'errorHandling': self.bashScriptErrorHandlingFragment
        }

        ebsPreRecipe = '''
#!/bin/bash
echo "=============================================="
echo "=== PRE-PROCESSING FOR BUILDING DISK IMAGE ==="
echo "=============================================="
echo "Download and install the ec2-api-tools"
cd /tmp
wget http://s3.amazonaws.com/ec2-downloads/ec2-api-tools.zip
%(errorHandling)s
cd /opt
unzip /tmp/ec2-api-tools.zip
rm -rf ec2-api-tools
mv ec2-api-tools-* ec2-api-tools
cd
source /opt/slipstream/client/scripts/slipstream.orchestrator.setup
%(errorHandling)s
echo "Creating EBS volume"
ss-create-volume %(size)s
%(errorHandling)s
volumeId=`cat /tmp/slipstream/volumeId`
echo "Creating mount directory"
mkdir -p %(mountDir)s
%(errorHandling)s
echo "Attaching EBS volume to mount directory via device"
ss-attach-volume --format --format-type %(fileSystemType)s $volumeId %(mountDir)s %(deviceName)s
%(errorHandling)s
echo "Publishing the new volume id: $volumeId to SlipStream block store"
volumeId=`cat /tmp/slipstream/volumeId`
ss-publish-volume $volumeId
%(errorHandling)s
''' % blockDir

        self._buildRemoteImage(timeout, ebsPreRecipe, installClient=True, createinstance=createinstance)

        # Update the node state
        self.setNodeStatusTerminated(self.defaultMachineName)

        return

    def buildImage(self, createinstance, strictversion, timeout):
        """ Build the virtual image """

        self.setNodeStatusBooting(self.defaultMachineName)

        # Check if we need to attach a block store to the image
        ebsPreRecipe = None
        qname = self._getModuleReference()
        module = self._getModule(qname)
        imageDetails = self._getImageDetails(module)
        blockDict = self.getBlockStoreData(imageDetails)

        if blockDict:
            ebsPreRecipe = '''
#!/bin/bash
echo "=============================================="
echo "=== PRE-PROCESSING FOR BUILDING DISK IMAGE ==="
echo "=============================================="
echo "Download and install the ec2-api-tools"
cd /tmp
wget http://s3.amazonaws.com/ec2-downloads/ec2-api-tools.zip
%(errorHandling)s
cd /opt
unzip /tmp/ec2-api-tools.zip
rm -rf ec2-api-tools
mv ec2-api-tools-* ec2-api-tools
cd
echo "Creating mount directory"
mkdir -p %(mountDir)s
%(errorHandling)s
echo "Attaching EBS volume to local device and mounting it"
ss-attach-volume %(copy)s %(volumeId)s %(mountDir)s %(deviceName)s
%(errorHandling)s
volumeId=`cat /tmp/slipstream/volumeId`
echo "Publishing the volume id: $volumeId to the execution instance"
ss-set ebs_%(ebsName)s $volumeId
%(errorHandling)s
echo "Publishing the volume id: $volumeId to a new image instance"
ss-publish-volume $volumeId
''' % blockDict

        # Instantiate the image
        credentials, info = self._buildRemoteImage(timeout, ebsPreRecipe, createinstance=createinstance)

        #
        # Save the new image
        #

        # bundle
        self._printSectionHead('Image creation')
        print >> sys.stderr, 'Bundling image'
        mntDirname = os.path.join(os.sep, 'mnt')

        keypairFilename = os.path.join(self.tmpdir, credentials['AWS_gsg-keypair_Name'])
        cmd = 'ssh -i ' + keypairFilename + ' root@' + info['dnsName'] + ' "cd ' + mntDirname \
              + '; ec2-bundle-vol -k ' + self.keyPemFileLocation \
              + ' -c ' + self.certPemFileLocation + ' -u XXX_AWS_Account_Number_XXX -r i386'
        # If we're using EBS, we need to tell the bundle command not to include the mounted device
        if blockDict:
            if 'mountDir' in blockDict:
                cmd += ' -e ' + blockDict['mountDir']
        cmd += '"'
        print >> sys.stderr, '    cmd:', cmd
        cmd = cmd.replace('XXX_AWS_Account_Number_XXX', credentials['AWS_Account_Number'].replace('-', ''))
        self._systemCall(cmd)

        # Create new S3 bucket to host the new image
        self._printSectionHead('Storage of image in cloud')
        username = self.getInstanceData('username')
        bucketName = username + '--slipstream--images'
        try:
            self._createBucket(bucketName)
        except:
            print >> sys.stderr, "Previous bucket creation failed, trying again, as S3 is sometimes a little flaky"
            self._createBucket(bucketName)

        # Build the S3 target bucket
        module = module.replace('+', '-')
        uploadTarget = bucketName + '/' + module + '/' + self.getDiid()

        # Upload
        print >> sys.stderr, 'Uploading image to S3'
        manifest = 'image.manifest.xml'
        cmd = 'ssh -i ' + keypairFilename + ' root@' + info[
            'dnsName'] + ' "cd ' + mntDirname + '; ec2-upload-bundle -b ' + uploadTarget \
            + ' -m /tmp/' + manifest + ' -a XXX_AWS_Access_Id_XXX -s XXX_AWS_Secret_Key_XXX"'
        print >> sys.stderr, '    cmd:', cmd
        cmd = cmd.replace('XXX_AWS_Access_Id_XXX', credentials[AmazonCredentialsPlugin.AWS_Access_Id])
        cmd = cmd.replace('XXX_AWS_Secret_Key_XXX', credentials[AmazonCredentialsPlugin.AWS_Secret_Key])

        # Try 4 times!!
        try:
            self._systemCall(cmd, True)
        except Exceptions.ClientError:
            self._systemCall(cmd, True)
        print >> sys.stderr, '    upload completed.'

        # Register
        print >> sys.stderr, 'Registering image with S3'
        cmd = 'ec2-register -K ' + self.keyPemFileLocation + ' -C ' + self.certPemFileLocation + ' ' + uploadTarget + '/' + manifest
        try:
            stdout = self._systemCall(cmd, True)
        except Exceptions.ClientError:
            stdout = self._systemCall(cmd, True)
        print >> sys.stderr, '    registration completed.'

        # Extract the AMI
        imageId = None
        for line in stdout:
            if line.startswith('IMAGE'):
                imageId = line.split('\t')[1].strip()
                break

        # Set the launch permission (if necessary)
        if 'publicPost' in imageDetails['authz']:
            print 'Setting AMI launch permission to public'
            cmd = 'ec2-modify-image-attribute  -K ' \
                  + self.keyPemFileLocation + ' -C ' \
                  + self.certPemFileLocation + ' ' \
                  + imageId + ' --launch-permission -a all'
            try:
                stdout = self._systemCall(cmd, True)
            except Exceptions.ClientError:
                stdout = self._systemCall(cmd, True)
            print '    permission set.'

        # Updating the image with the new imageId
        print >> sys.stderr, "Updating the image %s with the new AMI image id: '%s'" % (module, imageId)

        if not strictversion:
            # Retrieve the latest image qname, so that we update the right module version
            qname = imageDetails['name']

        self._updateImage(qname, {'imageId': imageId})
        print >> sys.stderr, 'Update completed.'

        # Update the node state
        self.setNodeStatusTerminated(self.defaultMachineName)

        return

    def createVolume(self, size, zone, timeout, snapshotId=None):
        """ Create a new volume """

        self._setupCredentials()

        #
        # Create the new EBS volume
        #

        # Extract the zone the current instance is running in
        instanceId = self.getInstanceData('instanceId')
        info = self._getImageInstanceInfo(instanceId)
        if not zone:
            zone = info['zone']

        # Create the volume
        print >> sys.stderr, 'Creating new volume in the zone:', zone
        if snapshotId:
            print >> sys.stderr, '    from the snapshot:', snapshotId
        if size:
            print >> sys.stderr, '    of size:', size

        cmd = 'ec2-create-volume -K %s -C %s -z %s' % (self.keyPemFileLocation,
                                                       self.certPemFileLocation,
                                                       zone)
        if snapshotId:
            cmd += ' --snapshot ' + snapshotId
        if size:
            cmd += ' -s ' + size

        res = self._systemCall(cmd)
        volumeId = res[-1].split()[1]
        print >> sys.stderr, 'Created new volume:', volumeId
        cmd = 'ec2-describe-volumes -K %s -C %s %s' % (self.keyPemFileLocation,
                                                       self.certPemFileLocation,
                                                       volumeId)
        # Wait for the volume to be created
        timer = 0
        sleepTime = 5
        status = 'Unknown'
        while True:
            res = self._systemCall(cmd)
            if snapshotId:
                index = 5
            else:
                index = 4
            status = res[-1].split()[index]
            if status == 'available':
                break
            if timeout != 0 and timer >= timeout:
                raise Exceptions.TimeoutException("Exceeded timeout limit (waiting for: %s" % cmd)
            print >> sys.stderr, "    Waiting for %s" % status
            sys.stdout.flush()
            time.sleep(sleepTime)
            timer += sleepTime

        return volumeId

    #    def createVersion(self,name,category,xbody=None):
    #        if not self._isValidCategory(category):
    #            raise ValueError('Unknown category: ' + category)
    #        url = self.navigatorServiceUrl + name
    #        shortModule = name.split('/')[:-1]
    #        xml = '''
    #<%sVersion
    #    name="%s/versions/1"
    #    module="%s"
    #    shortModule="%s"
    #    version="1"
    #    category="%s"
    #>
    #''' % (category,name,name,shortModule,category)
    #        if xbody:
    #            xml += xbody
    #        xml += "</%sVersion>" % category
    #        content = self._httpPut(url,xml)
    #        return content
    #    def decrementInfoSys(self, key):
    #        url = self.runServiceUrl + self.getDiid() + '/' + key + RestClient.urlIgnoreAbortAttributeFragment
    #        self._httpPost(url,"decrement=true")
    #        value = self._getInfoSys(key,True)
    #        if key == RestClient.initCounterName:
    #            self.setNodeStatusInitialized()
    #        elif key == RestClient.finalizeCounterName:
    #            self.setNodeStatusFinished()
    #        elif key == RestClient.terminateCounterName:
    #            self.setNodeStatusTerminated()
    #        return value

    #    def deleteModule(self,name):
    #        url = self.navigatorServiceUrl + name
    #        self._httpDelete(url)
    #        return

    def download(self, url):
        artefact = self._httpGet(url, "*/*")
        return artefact

    def exportModules(self, qnames, username=None, password=None):
        """ Export modules one at a time. """
        self.authenticate(username, password)
        modules = []
        for qname in qnames:
            content = self._httpGet(self.navigatorServiceUrl + qname)
            modules.append(content)
        return modules

    def getBlockStoreData(self, imageDetails=None):
        """ Retreive block store data, if it exists. """
        if not imageDetails:
            qname = self._getModuleReference()
            module = self._getModule(qname)
            imageDetails = self._getImageDetails(module)
        blockDict = {}
        if 'properties' in imageDetails and 'EBS_name' in imageDetails['properties']:
            ebsName = imageDetails['properties']['EBS_name']
            snapshotId = None
            fileSystemType = 'ext3'
            deviceName = '/dev/sdh'
            mountDir = '/mnt/data-store'
            size = '50'
            copy = '--copy'

            if 'properties' in imageDetails:
                parameters = imageDetails['properties']
                if 'EBS_devicename' in parameters:
                    deviceName = parameters['EBS_devicename']
                if 'EBS_filesystemtype' in parameters:
                    fileSystemType = parameters['EBS_filesystemtype']
                if 'EBS_mountdir' in parameters:
                    mountDir = parameters['EBS_mountdir']
                if 'EBS_nosnapshot' in parameters:
                    copy = ''
                if 'EBS_snapshotid' in parameters:
                    snapshotId = parameters['EBS_snapshotid']

            # If we have a snapshotId, we don't need to retrieve reference block store, but
            # if we don't, we need to retrieve the volumeId of the referenced block store
            # and start from there.
            if snapshotId:
                volumeId = snapshotId
            else:
                # Retrieve the volumeId from the reference module
                try:
                    blockStoreReference = imageDetails['properties']['EBS_reference']
                except KeyError:
                    raise Exceptions.ClientError(
                        'Missing block store reference and snapshot id to block store %s' % ebsName)

                blockStoreModule = self._getImageDetails(blockStoreReference)
                if 'volumeId' not in blockStoreModule:
                    raise Exceptions.ClientError('Missing volume id from module %s, make sure this referenced  \
                                                  block store has been built')
                volumeId = blockStoreModule['volumeId']

            blockDict = {
                'fileSystemType': fileSystemType,
                'deviceName': deviceName,
                'mountDir': mountDir,
                'size': size,
                'volumeId': volumeId,
                'copy': copy,
                'ebsName': ebsName,
                'errorHandling': self.bashScriptErrorHandlingFragment
            }
        return blockDict

    def getDiid(self):
        if self.diid:
            return self.diid
        if RestClient.SLIPSTREAM_DIID_ENV_NAME in os.environ:
            self.diid = os.environ[RestClient.SLIPSTREAM_DIID_ENV_NAME]
            return self.diid
            # Fetch the diid from the environment
        instanceDataDict = self.getInstanceData()
        try:
            return instanceDataDict['diid']
        except KeyError:
            self.diid = self._getLocalDiid()
        return self.diid

    def getImage(self, nodeName):
        """ Returns an dictionary containing the details of the image corresponding
            to the nodeName argument. """
        try:
            imageqname = self._getImages()[nodeName]
        except KeyError:
            raise Exceptions.ClientError('Failed to find nodename %s in the deployment' % nodeName)
        return self._getImageDetails(imageqname, withVirtualResolver=True)

    def getImageDetails(self, imageqname):
        return self._getImageDetails(imageqname)

    def getImageInstanceInfo(self, instanceId):
        info = self._getImageInstanceInfo(instanceId)
        return info

    def getInfoSys(self, key, block=True, timeout=0, ignoreAbort=False):

        _key = self._qualifyKey(key)

        if not block:
            value = self._getInfoSys(_key, ignoreAbort)
        else:
            value = None
            timer = 0
            while True:
                try:
                    value = self._getInfoSys(_key, ignoreAbort)
                except Exceptions.NotYetSetError:
                    pass
                if value is not None:
                    break
                if timeout != 0 and timer >= timeout:
                    raise Exceptions.TimeoutException(
                        "Exceeded timeout limit of %s waiting for key '%s' to be set" % (timeout, _key))
                print >> sys.stderr, "Waiting for %s" % _key
                sys.stdout.flush()
                sleepTime = 5
                time.sleep(sleepTime)
                timer += sleepTime
        return value

    def getInstanceData(self, key=None):
        """Retrieve specific instance data (e.g. user-data for EC2)"""
        return self.runtimeCloudConnectorModule.getConnector().getInstanceData(key)

    def getNodeName(self):

        if self.nodeName:
            return self.nodeName

        nodeName = self.getInstanceData('imagename')

        # Are we in the context of a deployment?
        category = self._getCategory()

        if category == 'Deployment':
            try:
                # is the nodename in the form: <nodename>.<index>
                # where index is an int?
                int(nodeName.split(RestClient.nodeMultiplicityIndexSeparator)[1])
            except IndexError:
                # no, so we add '.1' at the end
                nodeName += RestClient.nodeMultiplicityIndexSeparator + RestClient.nodeMultiplicityStartIndex
            except ValueError:
                raise Exceptions.ServerError('Invalid nodename: ' + nodeName + '. Index must be an int')
        self.nodeName = nodeName
        return self.nodeName

    def getNodeStateMessage(self):
        return self.getInfoSys(self.stateMessagePropertyName, block=False, ignoreAbort=True)

    def getNodeState(self):
        return self.getInfoSys(self.STATE_KEY, block=False, ignoreAbort=True)

    def getStatus(self, diid=None):
        """ Return the execution state """
        if diid:
            self._setDiid(diid)
        url = self.runServiceUrl + self.getDiid()
        content = self._httpGet(url)
        root = ET.fromstring(content)
        state = root.get('status')
        return state

    def getTargets(self):
        """Return the targets defined for the image version nodename"""
        nodename = self.getNodeName()
        images = self._getImages()
        if nodename not in images:
            raise Exceptions.ClientError("Can't find image node: " + nodename + " in current deployment")
        imageqname = images[nodename]
        url = self.navigatorServiceUrl + imageqname
        content = self._httpGet(url)
        root = ET.fromstring(content)
        targets = {}
        targetsNode = root.find('targets')
        if targetsNode:
            targetNodes = targetsNode.findall('target')
            for targetNode in targetNodes:
                runInBackgroundStr = targetNode.get('runInBackground')
                runInBackground = False
                if runInBackgroundStr:
                    if runInBackgroundStr.lower() == 'true':
                        runInBackground = True
                targets[targetNode.get('name')] = (targetNode.text, runInBackground)
        return targets

    def getUserCredentials(self, key):
        """ Return a dictionary of user properties."""
        credentials = self._getUserCredentials()
        if key is None:
            return credentials
        return {key: credentials[key]}

    def httpCall(self, url, method, body=None, contentType='application/xml', accept='application/xml'):
        resp, content = self._httpCall(url, method, body, contentType, accept)
        resp = resp
        return content

    def httpDelete(self, url):
        content = self._httpDelete(url)
        return content

    def httpGet(self, url):
        content = self._httpGet(url)
        return content

    def importModules(self, xmodules, username=None, password=None):
        """ Import modules one at a time. Expect a dict of qname:xml. """
        self.authenticate(username, password)
        for xmodule in xmodules:
            root = ET.fromstring(xmodule)
            qname = root.get('name')
            self._httpPut(self.navigatorServiceUrl + qname, xmodule)
        return

    def installPackages(self, packages):
        cmds = {}
        cmds['apt'] = ['apt-get --version', 'apt-get install -y %(packages)s']
        cmds['yum'] = ['yum --version', 'yum -y install %(packages)s']
        tool = None
        if self.verbose:
            print 'Detecting local packaging system'
        for key in cmds:
            try:
                if self.verbose:
                    print '    Trying:', key
                self._systemCall(cmds[key][0], False)
                tool = key
                if self.verbose:
                    print '    Using:', tool
                break
            except Exceptions.ClientError:
                pass
        if not tool:
            raise Exceptions.ClientError('Failed to detect a valid package installation tool')

        packageStr = ' '.join(packages)
        self._systemCall(cmds[tool][1] % {'packages': packageStr}, False)
        return

    def isStatusCompleted(self, status=None):
        if not status:
            try:
                status = self.getStatus()
            except:
                return False
        if status in ('Finished', 'Aborted', 'Deleted', 'Failed', 'Stopped'):
            return True
        else:
            return False

    def isStatusSuccess(self, status=None):
        if not status:
            try:
                status = self.getStatus()
            except:
                return False
        if status == 'Finished':
            return True
        else:
            return False

    def ping(self, username, password):
        """ Ping all SlipStream services """

        self._authenticate(username, password)
        # Ping the navigator root
        self.httpGet(self.navigatorServiceUrl)
        # Ping the execution instance root
        self.httpGet(self.runServiceUrl)
        # Ping the user
        _username = username
        if not _username:
            _username = self.getInstanceData('username')

        self.httpGet(self.authzServiceUrl + 'users/' + _username)

        # Ping the registration process resource
        try:
            self.httpGet(self.serverUrl + '/register/confirm/test/doesnexists')
        except Exceptions.ClientError:
            pass

        return

    def postProcess(self):
        """ Retrieve and execute the post-processing script for the deployment.  If the
            script is not defined return False, if it is, return True."""
        script = self._getDeploymentPostProcessingScript()
        if script:
            self._systemCall(script, False)
            return True
        else:
            return False

    def publishImageInfos(self):
        images = self._getImages()
        instanceIds = []
        instanceDict = {}  # {<instanceId>:<imageShortName>}
        for imageShortName in images:
            instanceId = self._getInfoSys(imageShortName + RestClient.NODE_PROPERTY_SEPARATOR + 'instanceid',
                                          ignoreAbort=True)
            instanceDict[instanceId] = imageShortName
            instanceIds.append(instanceId)

        instances = self._getImagesInstanceInfo(instanceIds)
        for instanceId in instances:
            imageName = instanceDict[instanceId]
            self.setInfoSys(imageName + RestClient.NODE_PROPERTY_SEPARATOR + 'instanceid', instanceId, ignoreAbort=True)
            self.setInfoSys(imageName + RestClient.NODE_PROPERTY_SEPARATOR + 'dnsName',
                            instances[instanceId]['dnsName'], ignoreAbort=True)
            self.setInfoSys(imageName + RestClient.NODE_PROPERTY_SEPARATOR + 'privateDnsName',
                            instances[instanceId]['privateDnsName'], ignoreAbort=True)

    def publishVolumeId(self, volumeId):
        """Update the volume id with a new volumeId, following successful volume creation """
        imageqname = self._getModuleReference()
        self._updateImage(imageqname, {'parameters--EBS_snapshotid': volumeId})
        return

    def s3Upload(self, file, destination, public=False, username=None, password=None, retry=True):
        self.authenticate(username, password)
        try:
            bucket, target = destination.split(':')
        except ValueError:
            bucket = destination
            target = os.path.basename(file)
        if not os.path.exists(file):
            raise Exceptions.ClientError('Couldn\'t find input file: %s' % file)
        if self.verbose:
            print 'Uploading %s to bucket %s and object %s' % (file, bucket, target)
        object = open(file).read()
        try:
            credentials = self._getUserCredentials()
            # .lower() the bucketname since S3 fails with upper chars
            connector = self.storageCloudConnectorModule. \
                getConnector(credentials[AmazonCredentialsPlugin.AWS_Access_Id],
                             credentials[AmazonCredentialsPlugin.AWS_Secret_Key])
            response = connector.put(bucket, target, object, headers={'Content-Type': 'application/x-compressed'})
            if response.http_response.status == 404:
                # Looks like the bucket doesn't exist, so we create it and call the upload method again
                self._createBucket(bucket)
                return self.s3Upload(file, destination)
            elif not (response.http_response.status == 201 or response.http_response.status == 200):
                raise ValueError('Error uploading file to S3.  Error code: %s with reason: %s' % (
                    response.http_response.status, response.message))
        except:
            if retry:
                return self.s3Upload(file, destination, public, retry=False)
            raise
        if public:
            self._setS3AclPublic(bucket, target, connector)

        return

    def s3Download(self, remotePath, username=None, password=None, retry=True):
        self.authenticate(username, password)
        try:
            bucket, path = remotePath.split(':')
        except ValueError:
            raise Exceptions.ClientError('Invalid remote path format')
        try:
            credentials = self._getUserCredentials()
        except socket.error:
            raise Exceptions.NetworkError('Failed to contact SlipStream server for credential authentication, please check your network connection '
                                          'and that the SlipStream server is alive at: ' + self.authzServiceUrl)
        try:
            connector = self.storageCloudConnectorModule. \
                getConnector(credentials[AmazonCredentialsPlugin.AWS_Access_Id],
                             credentials[AmazonCredentialsPlugin.AWS_Secret_Key])
            response = connector.get(bucket, path)
            if not (response.http_response.status == 201 or response.http_response.status == 200):
                raise ValueError('Error downloading file: %s.  Error code: %s with reason: %s' % (
                    remotePath, response.http_response.status, response.message))
        except:
            if retry:
                return self.s3Download(remotePath, retry=False)
            raise
        return response.body

    def setInfoSys(self, key, value, ignoreAbort=False):
        """ Set the key to the value"""
        _key = self._qualifyKey(key)

        url = self.runServiceUrl + self.getDiid() + '/' + _key

        if ignoreAbort:
            url += RestClient.urlIgnoreAbortAttributeFragment

        try:
            self._httpPut(url, "value=" + str(value))
        except Exceptions.AbortException:
            if ignoreAbort:
                pass
            else:
                raise
        return

    def setLocalDiid(self, diid):
        diidFilePath = self._setDiid(diid)
        return diidFilePath

    # Execution global status

    def setStatusStopped(self):
        self._setState('Stopped')
        return

    def setStatusFailing(self):
        self._setState('Failing')
        return

    def setStatusFailed(self):
        self._setState('Failed')
        return

    def setStatusAborting(self, reason=None, nodename=None):
        self._setState('Aborting')

        # Set as well the key/value pair
        self.abortInfoSys(reason, nodename=nodename)

        return

    def setStatusRunning(self):
        self._setState('Running')
        return

    def setStatusFinished(self):
        self._setState('Finished')
        return

    #
    # Node running states
    #
    def setNodeStatusBooting(self, nodename=None):
        self._setNodeStatus('Booting', active=True, nodename=nodename)
        return

    def setNodeStatusInitializing(self, nodename=None):
        self._setNodeStatus('Initializing', active=True, nodename=nodename)
        return

    def setNodeStatusInitialized(self, nodename=None):
        self._setNodeStatus('Initialized', active=True, nodename=nodename)
        return

    def setNodeStatusRunning(self, nodename=None):
        self._setNodeStatus('Running', active=True, nodename=nodename)
        return

    def setNodeStatusFinished(self, nodename=None):
        self._setNodeStatus('Run completed', active=True, nodename=nodename)
        return

    def setNodeStatusTerminating(self, nodename=None):
        self._setNodeStatus('Sending reports', active=True, nodename=nodename)
        return

    def setNodeStatusTerminated(self, nodename=None):
        self._setNodeStatus('Finished', final=True, nodename=nodename)
        return

    def setNodeStatusShutdown(self, nodename=None):
        self._setNodeStatus('Shutdown', final=True, nodename=nodename)
        return

    #
    # Node failure states
    #
    def setNodeStatusFailing(self, nodename=None, reason=None):
        self._setNodeStatus('Failing', active=True, failure=True, nodename=nodename)

        # Set abort flag
        self.abortInfoSys(reason, nodename=nodename)
        self.isAbort = True

        # Set the general status
        self.setStatusFailing()

        return

    def setNodeStatusFailed(self, nodename=None):
        self._setNodeStatus('Failed', failure=True, final=True, nodename=nodename)
        return

    def setNodeStatusAborting(self, nodename=None, reason=None):
        self._setNodeStatus('Aborting', active=True, nodename=nodename)

        # Set the general status
        self.setStatusAborting(reason, nodename=nodename)

        self.isAbort = True
        return

    def setNodeStatusAborted(self, nodename=None):
        self._setNodeStatus('Aborted', final=True, nodename=nodename)
        return

    def startImages(self):
        # Start images
        images = self._getImages()
        credentials = self._getUserCredentials()
        username = self.getInstanceData('username')
        password = self.getInstanceData('password')
        #category = self.getInstanceData('version.category')
        clientUrl = self.getInstanceData('clienturl')
        userDataDict = {}
        for imageShortName, imageQname in images.items():

            # Update the machine status
            self.setNodeStatusBooting(imageShortName)

            details = self._getImageDetails(imageQname, withVirtualResolver=True)

            # Check that an imageId is available, otherwise we can't execute the deployment
            if 'imageId' not in details:
                raise Exceptions.ClientError('Image %s was not built prior to this execution' % imageShortName)
            print '    Instantiating image: %s %s %s' % (imageShortName, imageQname, details['imageId'])

            self.assignDefaultAwsSecurityGroupNameIfNotDefined()

            # Add constant parameters to the user-data
            params = {}
            if 'properties' in details:
                params.update(details['properties'])
            if 'outputParameters' in details:
                params.update(details['outputParameters'])
            if 'inputParameters' in details:
                params.update(details['inputParameters'])

            userData = self._createUserDataString(self.getDiid(), self.serverUrl, username, password, category,
                                                  clientUrl, imageShortName, parameters=params)

            instanceId = self._instentiateImage(details['imageId'], userData, credentials)

            # Set ignoreAbort in case the abort flag is raised, since
            # we still want to keep track of the image instance id
            self.setInfoSys(imageShortName + RestClient.NODE_PROPERTY_SEPARATOR + 'instanceid', instanceId,
                            ignoreAbort=True)

            userDataDict[imageShortName] = userData

        return userDataDict

    def assignDefaultAwsSecurityGroupNameIfNotDefined(self):
        credentials = self._getUserCredentials()
        AWS_Security_Group_Name = 'AWS_Security_Group_Name'
        if not AWS_Security_Group_Name in credentials or credentials[AWS_Security_Group_Name] is None:
            credentials[AWS_Security_Group_Name] = 'default'
        return

    def stopOrchestratorImage(self):
        instanceId = self.getInstanceData('instanceId')
        print 'Stopping orchestrator instance: %s' % instanceId
        self.setNodeStatusShutdown(RestClient.orchestratorName)
        self.terminateInstances([instanceId])
        return instanceId

    def stopImages(self, orchestratorOnly=False):
        """ Stop the running images or the orchestrator.  The stopping behaviour is controlled
            by the user profile properties."""

        instanceIds = []
        runForever = False
        if self.state == 'Stopped':
            print 'Execution stopped'
            return instanceIds

        if self.isRunForeverOnSuccessSet():
            if self.isStatusSuccess():
                runForever = True
                print 'On user request, letting the deployment run forever'

        # Check if, on error, we should let the deployment run forever
        if self.isRunForeverOnFailureSet():
            if not self.isStatusSuccess():
                runForever = True
                sys.stderr.write(
                    "Execution failed and '%s' flag set, stopping execution and letting instances running\n" % UserCredentialsManager.execOnErrorRunForeverUserModelParameter)
                self.setStatusStopped()

        if not runForever:
            instanceIds = self.instantiatedImages
            self.terminateInstances(instanceIds)

        return instanceIds

    def isRunForeverOnSuccessSet(self):
        credentials = self._getUserCredentials(validate=False)
        if UserCredentialsManager.execOnSuccessRunForeverUserModelParameter in credentials \
                and credentials[UserCredentialsManager.execOnSuccessRunForeverUserModelParameter] == UserCredentialsManager.valueWhenTrue:
            return True
        else:
            return False

    def isRunForeverOnFailureSet(self):
        credentials = self._getUserCredentials(validate=False)
        if UserCredentialsManager.execOnErrorRunForeverUserModelParameter in credentials \
                and credentials[UserCredentialsManager.execOnErrorRunForeverUserModelParameter] == UserCredentialsManager.valueWhenTrue:
            return True
        else:
            return False

    def terminateInstances(self, instanceIds):
        for instanceId in instanceIds:
            print '    stopping image instance: %s' % instanceId
        credentials = self._getUserCredentials(validate=False)
        response = self.computingCloudConnectorModule.getConnector(
            credentials[AmazonCredentialsPlugin.AWS_Access_Id],
            credentials[AmazonCredentialsPlugin.AWS_Secret_Key]
        ).terminate_instances(instanceIds)
        if response.is_error:
            raise Exceptions.ServerError(
                'Failed stopping image instances %s with reason: %s' % (' '.join(instanceIds), str(response)))

        if self.verbose:
            print response.parse()
        return

    def submit(self, module, username, password):
        self._authenticate(username, password)
        url = self.runServiceUrl
        content = self._httpPost(url, body="refqname=%s" % module, contentType='text/plain')
        return content

    def uploadReport(self):
        nodeName = self.getNodeName()
        reportsDir = RestClient.reportsdir
        if not os.path.exists(reportsDir):
            raise Exceptions.ClientError("Coudn't find report: %s" % reportsDir)
        if not os.path.isdir(reportsDir):
            raise Exceptions.ClientError("Report %s not a directory" % reportsDir)

        try:
            oldDir = os.getcwd()
            os.chdir(reportsDir)
            finalReport = nodeName + '.tgz'
            tar = tarfile.open(finalReport, 'w:gz')
            for name in os.listdir('.'):
                tar.add(name, arcname=os.path.join(nodeName, name))
            tar.close()
            finalReport = os.path.join(reportsDir, finalReport)
        finally:
            os.chdir(oldDir)
        self._uploadReport(finalReport)
        return

    def waitForCounter(self, key, timeout=None, targetValue=0, ignoreAbort=True):
        timer = 0
        while True:
            value = self._getInfoSys(key, ignoreAbort)
            if int(value) <= targetValue:
                break
            if timeout and timer >= timeout:
                raise Exceptions.TimeoutException(
                    'Exceeded timeout limit of %s while waiting for key %s' % (timeout, key))
            print >> sys.stderr, "    %s currently at '%s', waiting for it to drop to '%s'" % (key, value, targetValue)
            sys.stdout.flush()
            sleepTime = 5
            time.sleep(sleepTime)
            timer += sleepTime
        return


class Credentials(object):
    def __init__(self, parameters={}, cloudCredentialsPlugin=None):
        self._parameters = parameters
        self.cloudCredentialsPlugin = cloudCredentialsPlugin
        return

    def __getitem__(self, name):
        try:
            parameter = self._parameters[name]
        except:
            parameter = self.getCloudCredentialsParameter(name)
        return parameter

    def getCloudCredentialsParameter(self, name):
        if self.cloudCredentialsPlugin:
            return self.cloudCredentialsPlugin[name]
        else:
            raise Exceptions.NotFoundError('Paramerter %s is not defined' % name)
        return


class UserCredentialsManager(Credentials):
    execOnSuccessRunForeverUserModelParameter = 'Exec_On_success_run_forever'
    execOnErrorRunForeverUserModelParameter = 'Exec_On_error_run_forever'
    valueWhenTrue = 'on'

    def __init__(self, parameters={}, cloudCredentialsPlugin=None):
        super(UserCredentialsManager, self).__init__(parameters, cloudCredentialsPlugin)
        return


class AmazonCredentialsPlugin(Credentials):
    AWS_Secret_Key = 'AWS_Secret_Key'
    AWS_Access_Id = 'AWS_Access_Id'

    def __init__(self, parameters={}, cloudCredentialsPlugin=None):
        super(AmazonCredentialsPlugin, self).__init__(parameters, cloudCredentialsPlugin)
        return


# TODO

class ContextualizationManager:
    def __init__(self):
        pass


class ConnectorFactory:
    def __init__(self):
        pass
