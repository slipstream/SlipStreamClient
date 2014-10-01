
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from slipstream.command.CloudClientCommand import CloudClientCommand
from slipstream.NodeDecorator import KEY_RUN_CATEGORY
from slipstream.ConfigHolder import ConfigHolder
from slipstream.util import nostdouterr

class DescribeInstancesCommand(CloudClientCommand):

    def _vm_get_state(self, cc, vm):
        raise NotImplementedError()

    def _vm_get_id(self, cc, vm):
        return cc._vm_get_id(vm)

    def _list_instances(self, cc):
        return cc.list_instances()

    def __init__(self, timeout=30):
        super(DescribeInstancesCommand, self).__init__(timeout)

    def do_work(self):
        with nostdouterr():
            cc, vms = self.describe_instances()
        self._print_results(cc, vms)

    def describe_instances(self):
        cc = self.get_connector_class()(ConfigHolder(options={'verboseLevel': 0,
                                                              'http_max_retries': 0,
                                                              KEY_RUN_CATEGORY: ''},
                                                     context={'foo': 'bar'}))
        cc._initialization(self.user_info, **self.get_initialization_extra_kwargs())
        vms = self._list_instances(cc)
        return cc, vms


    def _print_results(self, cc, vms):
        print "id state"
        for vm in vms:
            print self._vm_get_id(cc, vm), self._vm_get_state(cc, vm)

