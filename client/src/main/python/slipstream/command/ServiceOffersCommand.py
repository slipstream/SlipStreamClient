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

import requests

from slipstream.api import Api, SlipStreamError
from slipstream.ConfigHolder import ConfigHolder
from slipstream.NodeDecorator import KEY_RUN_CATEGORY
from slipstream.command.CloudClientCommand import CloudClientCommand


class ServiceOffersCommand(CloudClientCommand):

    DEFAULT_TIMEOUT = 600
    EXCHANGE_RATES_SERVICE_URL = 'https://api.fixer.io/latest'

    DRY_RUN_KEY = 'dry-run'
    COUNTRY_KEY = 'country'
    SS_ENDPOINT_KEY = 'ss-url'
    SS_USERNAME_KEY = 'ss-user'
    SS_PASSWORD_KEY = 'ss-pass'
    BASE_CURRENCY_KEY = 'currency'
    CONNECTOR_NAME_KEY = 'connector-name'

    def __init__(self):
        super(ServiceOffersCommand, self).__init__()

        self.cc = None
        self.base_currency = 'EUR'
        self._exchange_rates = {}

    def _get_default_timeout(self):
        return self.DEFAULT_TIMEOUT

    def _list_vm_sizes(self):
        """
        Return a list of available VM sizes.
        """
        return self.cc._list_vm_sizes() if self.cc else None

    def _get_cpu(self, vm_size):
        """
        Extract and return the amount of vCPU from the specified vm_size.
        :param vm_size: A 'size' object as in the list returned by _list_vm_sizes().
        :rtype int
        """
        return self.cc._size_get_cpu(vm_size) if self.cc else None

    def _get_ram(self, vm_size):
        """
        Extract and return the size of the RAM memory in MB from the specified vm_size.
        :param vm_size: A 'size' object as in the list returned by _list_vm_sizes().
        :rtype int
        """
        return self.cc._size_get_ram(vm_size) if self.cc else None

    def _get_disk(self, vm_size):
        """
        Extract and return the size of the root disk in GB from the specified vm_size.
        :param vm_size: A 'size' object as in the list returned by _list_vm_sizes().
        :rtype float
        """
        return self.cc._size_get_disk(vm_size) if self.cc else None

    def _get_instance_type(self, vm_size):
        """
        Extract and return the instance type from the specified vm_size.
        :param vm_size: A 'size' object as in the list returned by _list_vm_sizes().
        :rtype int
        """
        return self.cc._size_get_instance_type(vm_size) if self.cc else None

    def _get_country(self):
        """
        Return the 2-letters symbol of the country where the Cloud reside.
        """
        return self.get_option(self.COUNTRY_KEY)

    def _get_supported_os(self, vm_size):
        """
        Return a list of supported OS for the specified vm_size
        :param vm_size: A vm_size object as returned by the method _list_vm_sizes() of the connector
        """
        return ['linux', 'windows']

    def _get_price(self, vm_size, os, root_disk_size=None):
        """
        Get the price for a give vm_size, OS and optionnal root disk size
        :param vm_size: A vm_size object as returned by the method _list_vm_sizes() of the connector
        :param os: The name of the operating system type (eg: 'linux', 'suse', 'windows')
        :param root_disk_size: The size of the root disk in GB
        :return: A tuple containing the price per hour and the currency. eg:(0.24, 'USD') )
        """
        return (None, None)

    def _get_root_disk_sizes(self, vm_size, os):
        """
        Return a list of available root disk sizes for the given vm_size
        :param vm_size: A vm_size object as returned by the method _list_vm_sizes() of the connector
        :param os: The name of the operating system type (eg: 'linux', 'suse', 'windows')
        :return: A list of available disk sizes
        """
        return [10, 25, 50, 100, 200, 400, 600, 800, 1000, 1600, 2000, 4000, 6000, 8000, 10000]

    def _get_root_disk_type(self, vm_size):
        """
        Return the type of the root disk (eg: HDD, SSD, EBS, ...)
        :param vm_size: A vm_size object as returned by the method _list_vm_sizes() of the connector
        """
        return 'Unknown'

    def _get_billing_period(self, vm_size):
        """
        Return the billing period
        :param vm_size: A vm_size object as returned by the method _list_vm_sizes() of the connector
        """
        return 'MIN'

    def _get_platform(self, vm_size):
        """
        Return the name of platform
        :param vm_size: A vm_size object as returned by the method _list_vm_sizes() of the connector
        """
        pass

    def _get_extra_attributes(self, vm_size):
        """
        Return the billing period
        :param vm_size: A vm_size object as returned by the method _list_vm_sizes() of the connector
        """
        pass

    def get_exchange_rate(self, src_currency, dst_currency):
        if dst_currency not in self._exchange_rates:
            self._exchange_rates[dst_currency] = requests.get(self.EXCHANGE_RATES_SERVICE_URL,
                                                              params={'base': dst_currency}).json().get('rates', {})
        return 1.0 / self._exchange_rates.get(dst_currency, {}).get(src_currency)

    def convert_currency(self, src_currency, dst_currency, amount):
        return amount * self.get_exchange_rate (src_currency, dst_currency) if src_currency != dst_currency else amount

    def _generate_service_offer(self, connector_instance_name, cpu, ram, root_disk, root_disk_type, os, price,
                                instance_type=None, billing_period='MIN', platform=None, extra_attributes=None):
        country = self._get_country()
        resource_type = 'VM'
        resource_class = 'standard'

        if not instance_type:
            instance_type = '{:d}/{:d}/{:d}'.format(cpu,ram, root_disk)

        if not platform and self.cc:
            platform = self.cc.cloudName

        service_offer = {
            "name": "{:d}/{:d}/{:d} {} [{}] ({})".format(cpu,ram, root_disk, os, country, instance_type),
            "description": "{} ({}) with {:d} vCPU, {:d} MiB RAM, {:d} GiB root disk, {} [{}] ({})"
                .format(resource_type, resource_class, cpu, ram, root_disk, os, country, instance_type),
            "resource:vcpu": cpu,
            "resource:ram": ram,
            "resource:disk": root_disk,
            "resource:diskType": root_disk_type,
            "resource:type": resource_type,
            "resource:class": resource_class,
            "resource:country": country,
            "resource:platform": platform,
            "resource:operatingSystem": os,
            "price:unitCost": price,
            "price:unitCode": "C62",
            "price:freeUnits": 0,
            "price:currency": self.base_currency,
            "price:billingUnitCode": "HUR",
            "price:billingPeriodCode": billing_period,
            "schema-org:name": instance_type,
            "connector": {"href": connector_instance_name},
            "acl" : {
                "owner" : {
                    "type" : "ROLE",
                    "principal" : "ADMIN"
                },
                "rules" : [ {
                    "principal" : "USER",
                    "right" : "VIEW",
                    "type" : "ROLE"
                }, {
                    "principal" : "ADMIN",
                    "right" : "ALL",
                    "type" : "ROLE"
                } ]
            },
        }
        if extra_attributes:
            service_offer.update(extra_attributes)

        return service_offer

    def _generate_service_offers(self, connector_instance_name):
        service_offers = []

        for vm_size in self._list_vm_sizes():
            cpu = int(self._get_cpu(vm_size))
            ram = int(self._get_ram(vm_size))
            root_disk_type = self._get_root_disk_type(vm_size)
            instance_type = self._get_instance_type(vm_size)
            billing_period = self._get_billing_period(vm_size)
            platform = self._get_platform(vm_size)
            extra_attributes = self._get_extra_attributes(vm_size)

            for os in self._get_supported_os(vm_size):
                for root_disk in self._get_root_disk_sizes(vm_size, os):
                    price = None
                    raw_price, currency = self._get_price(vm_size, os, root_disk)
                    if raw_price is not None:
                        price = self.convert_currency(currency, self.base_currency, raw_price)

                    service_offers.append(self._generate_service_offer(connector_instance_name, cpu, ram, root_disk,
                                                                       root_disk_type, os, price, instance_type,
                                                                       billing_period, platform, extra_attributes))
        return service_offers

    def do_work(self):
        ch = ConfigHolder(options={'verboseLevel': 0,
                                   'retry': False,
                                   KEY_RUN_CATEGORY: ''},
                          context={'foo': 'bar'})
        self.cc = self.get_connector_class()(ch)
        self.cc._initialization(self.user_info, **self.get_initialization_extra_kwargs())

        self.base_currency = self.get_option(self.BASE_CURRENCY_KEY)

        dry_run = self.get_option(self.DRY_RUN_KEY)
        ss_endpoint = self.get_option(self.SS_ENDPOINT_KEY)
        ss_username = self.get_option(self.SS_USERNAME_KEY)
        ss_password = self.get_option(self.SS_PASSWORD_KEY)
        connector_instance_name = self.get_option(self.CONNECTOR_NAME_KEY)

        ssapi = Api(endpoint=ss_endpoint, cookie_file=None, insecure=True)
        if not dry_run:
            ssapi.login(ss_username, ss_password)

        service_offers = self._generate_service_offers(connector_instance_name)

        for service_offer in service_offers:
            if dry_run:
                print('\nService offer {}:\n{}'.format(service_offer['name'], service_offer))
            else:
                cimi_filter = 'connector/href="{}" and description="{}"'.format(connector_instance_name, service_offer['description'])
                search_result = ssapi.cimi_search('serviceOffers', filter=cimi_filter)
                result_count = len(search_result.resources_list)

                if result_count == 0:
                    print('\nAddinging the following service offer {} to {}...\n{}'.format(service_offer['name'], ss_endpoint, service_offer))
                    if not dry_run:
                        ssapi.cimi_add('serviceOffers', service_offer)
                elif result_count == 1:
                    print('\nUpdating the following service offer {} to {}...\n{}'.format(service_offer['name'], ss_endpoint, service_offer))
                    if not dry_run:
                        ssapi.cimi_edit(search_result.resources_list[0].id, service_offer)
                else:
                    print('\n!!! Warning duplicates found of following service offer on {} !!!/n{}'.format(ss_endpoint, service_offer['name']))
        print('\n\nCongratulation, executon completed.')

    def _set_command_specific_options(self, parser):
        parser.add_option('--' + self.BASE_CURRENCY_KEY, dest=self.BASE_CURRENCY_KEY,
                          help='Currency to use', default='EUR', metavar='CURRENCY')

        parser.add_option('--' + self.COUNTRY_KEY, dest=self.COUNTRY_KEY,
                          help='Country where the Cloud reside', default='Unknown', metavar='COUNTRY')

        parser.add_option('--' + self.CONNECTOR_NAME_KEY, dest=self.CONNECTOR_NAME_KEY,
                          help='Connector instance name to be used as a connector href for service offers',
                          default=None, metavar='CONNECTOR_NAME')

        parser.add_option('--' + self.SS_ENDPOINT_KEY, dest=self.SS_ENDPOINT_KEY,
                          help='SlipStream endpoint used where the service offers are pushed to. (default: https://nuv.la)',
                          default='https://nuv.la', metavar='URL')

        parser.add_option('--' + self.SS_USERNAME_KEY, dest=self.SS_USERNAME_KEY,
                          help='Username to be used on SlipStream Endpoint',
                          default=None, metavar='USERNAME')

        parser.add_option('--' + self.SS_PASSWORD_KEY, dest=self.SS_PASSWORD_KEY,
                          help='Password to be used on SlipStream Endpoint',
                          default=None, metavar='PASSWORD')

        parser.add_option('--' + self.DRY_RUN_KEY, dest=self.DRY_RUN_KEY,
                          help='Just print service offers to stdout and exit',
                          action='store_true')

    def _get_command_mandatory_options(self):
        return [self.CONNECTOR_NAME_KEY]

