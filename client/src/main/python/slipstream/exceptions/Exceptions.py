"""
 SlipStream Client
 =====
 Copyright (C) 2014 SixSq Sarl (sixsq.com)
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


class ServerError(Exception):
    def __init__(self, *args):
        self.args = args

    def __str__(self):
        return repr(self.args)


class CloudError(ServerError):
    pass


class VolumeError(CloudError):
    pass


class NetworkError(ServerError):
    pass


class SecurityError(ServerError):
    pass


class ClientError(Exception):
    def __init__(self, arg, code=None):
        self.arg = arg
        self.code = code

    def __str__(self):
        return self.arg


class AbortException(ClientError):
    pass


class NotFoundError(ClientError):
    pass


class NotYetSetException(ClientError):
    pass


class ConfigurationError(ClientError):
    pass


class TimeoutException(ClientError):
    pass


class TerminalStateException(ClientError):
    pass


class ExecutionException(ClientError):
    pass


class ParameterNotFoundException(ClientError):
    pass
