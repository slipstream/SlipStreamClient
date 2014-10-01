
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from slipstream.command.CloudClientCommand import CloudClientCommand
from slipstream.NodeDecorator import KEY_RUN_CATEGORY
from slipstream.ConfigHolder import ConfigHolder

class TerminateInstancesCommand(CloudClientCommand):

    INSTANCE_IDS_KEY = 'instance-ids'

    def __init__(self, timeout=600):
        print __name__
        super(TerminateInstancesCommand, self).__init__(timeout)

    def _set_command_specific_options(self, parser):
        parser.add_option('--' + self.INSTANCE_IDS_KEY, dest=self.INSTANCE_IDS_KEY,
                          help='Instance ID (can be used multiple times)', action='append', default=[], metavar='ID')

    def _get_command_mandatory_options(self):
        return [self.INSTANCE_IDS_KEY]

    def do_work(self):
        ids = self.get_option(self.INSTANCE_IDS_KEY)
        cc = self.get_connector_class()(ConfigHolder(options={'verboseLevel': 0,
                                                              'http_max_retries': 0,
                                                              KEY_RUN_CATEGORY: ''},
                                                     context={'foo': 'bar'}))
        cc._initialization(self.user_info, **self.get_initialization_extra_kwargs())

        if cc.has_capability(cc.CAPABILITY_VAPP):
            cc.stop_vapps_by_ids(ids)
        else:
            cc.stop_vms_by_ids(ids)

