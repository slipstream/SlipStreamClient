
from slipstream.cloudconnectors.CloudClientCommand import CloudClientCommand
from slipstream.cloudconnectors.cloudstack.CloudStackClientCloud import CloudStackClientCloud


class CloudStackCommand(CloudClientCommand):

    def __init__(self):
        self.PROVIDER_NAME = CloudStackClientCloud.cloudName
        super(CloudStackCommand, self).__init__()

    def _setCommonOptions(self):
        self.parser.add_option('--key', dest='key',
                help='Key',
                default='', metavar='KEY')

        self.parser.add_option('--secret', dest='secret',
                help='Secret',
                default='', metavar='SECRET')

        self.parser.add_option('--endpoint', dest='endpoint',
                help='Endpoint',
                default='', metavar='ENDPOINT')

        self.parser.add_option('--zone', dest='zone',
                help='Zone',
                default='', metavar='ZONE')

    def _checkOptions(self):
        if not all((self.options.key, self.options.secret,
                    self.options.endpoint, self.options.zone)):
            self.parser.error('Some options were not given values. '
                              'All options are mandatory.')
        self.checkOptions()

    def _setUserInfo(self):
        self.userInfo[self.PROVIDER_NAME + '.username'] = self.options.key
        self.userInfo[self.PROVIDER_NAME + '.password'] = self.options.secret
        self.userInfo[self.PROVIDER_NAME + '.endpoint'] = self.options.endpoint
        self.userInfo[self.PROVIDER_NAME + '.zone'] = self.options.zone
