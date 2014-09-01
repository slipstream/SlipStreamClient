
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import sys

from slipstream.command.CloudClientCommand import CloudClientCommand
from slipstream.NodeDecorator import KEY_RUN_CATEGORY, RUN_CATEGORY_DEPLOYMENT
from slipstream.NodeInstance import NodeInstance
from slipstream.ConfigHolder import ConfigHolder
from slipstream.util import nostdouterr


saved_stdout = sys.stdout

def publish_vm_info(self, vm, node_instance):
    print >> saved_stdout, '%s,%s' % (self._vm_get_id(vm), self._vm_get_ip(vm))


class RunInstancesCommand(CloudClientCommand):

    IMAGE_ID_KEY =  'image-id'
    PLATFORM_KEY = 'platform'
    NETWORK_TYPE = 'network-type'

    def get_cloud_specific_node_inst_cloud_params(self):
        return {}

    def __init__(self, timeout=600):
        print __name__
        super(RunInstancesCommand, self).__init__(timeout)

    def _set_command_specific_options(self, parser):
        parser.add_option('--' + self.IMAGE_ID_KEY, dest=self.IMAGE_ID_KEY, help='Image ID',
                          default='', metavar='IMAGEID')

        parser.add_option('--' + self.PLATFORM_KEY, dest=self.PLATFORM_KEY,
                          help='Platform (eg: Ubuntu, CentOS, Windows, ...)', default='linux', metavar='PLATFORM')

        parser.add_option('--' + self.NETWORK_TYPE, dest=self.NETWORK_TYPE,
                          help='Network type (public or private)',
                          default='Public', metavar='NETWORK-TYPE')

    def _get_command_mandatory_options(self):
        return [self.IMAGE_ID_KEY,
                self.PLATFORM_KEY,
                self.NETWORK_TYPE]

    def get_node_instance(self):
        return NodeInstance({
            'name': self.get_node_instance_name(),
            'cloudservice': self._cloud_instance_name,
            'image.platform': self.get_option(self.PLATFORM_KEY),
            'image.imageId': self.get_option(self.IMAGE_ID_KEY),
            'image.id': self.get_option(self.IMAGE_ID_KEY),
            'network': self.get_option(self.NETWORK_TYPE)
        })

    def do_work(self):
        node_instance = self.get_node_instance()
        node_instance.set_cloud_parameters(self.get_cloud_specific_node_inst_cloud_params())

        with nostdouterr():
            self._run_instance(node_instance)

    def _run_instance(self, node_instance):
        nodename = node_instance.get_name()

        cloud_connector_class = self.get_connector_class()
        cloud_connector_class._publish_vm_info = publish_vm_info

        cc = cloud_connector_class(ConfigHolder(options={'verboseLevel': 0,
                                                         'http_max_retries': 0,
                                                         KEY_RUN_CATEGORY: RUN_CATEGORY_DEPLOYMENT},
                                                context={'foo': 'bar'}))

        cc.start_nodes_and_clients(self.user_info, {nodename: node_instance})












