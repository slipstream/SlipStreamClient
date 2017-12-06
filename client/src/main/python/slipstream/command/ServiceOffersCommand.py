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

    RESOURCE_SERVICE_ATTRIBUTE_NAMESPACES = 'serviceAttributeNamespaces'

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
        self.ssapi = None
        self.base_currency = 'EUR'
        self._exchange_rates = {}

    def _initialize(self):
        """
        This method is called once command arguments have been parsed and self.cc and self.ssapi are available
        """
        pass

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
        disk_size = self._get_disk(vm_size)
        if disk_size is not None and disk_size > 0:
            return [disk_size]

        return [10, 25, 50, 100, 200, 400, 600, 800, 1000, 1600, 2000, 4000, 6000, 8000, 10000]

    def _get_root_disk_type(self, vm_size):
        """
        Return the type of the root disk (eg: HDD, SSD, EBS, ...)
        :param vm_size: A vm_size object as returned by the method _list_vm_sizes() of the connector
        """
        return 'Unknown'

    def _get_billing_unit(self, vm_size):
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

    def _get_prefix(self):
        """
        Return the prefix (namespace) to use for extra attributes
        :rtype: str
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

    @staticmethod
    def _generate_service_attribute_namespace(prefix, description=None, acl=None):

        if acl is None:
            acl = {
                "owner": {
                    "principal": "ADMIN",
                    "type": "ROLE"
                },
                "rules": [{
                    "principal": "USER",
                    "type": "ROLE",
                    "right": "VIEW"
                }, {
                    "type": "ROLE",
                    "principal": "ADMIN",
                    "right": "ALL"
                }]
            }

        san = {
            "prefix": prefix,
            "id": "service-attribute-namespace/" + prefix,
            "acl": acl,
            "resourceURI": "http://sixsq.com/slipstream/1/ServiceAttributeNamespace",
            "uri": "http://sixsq.com/slipstream/schema/1/" + prefix
        }

        if description is not None:
            san['description'] = description

        return san

    def _add_service_attribute_namespace_if_not_exist(self, prefix, description=None, acl=None):
        verbose = self.get_option('verbose')

        cimi_resp = self.ssapi.cimi_search(self.RESOURCE_SERVICE_ATTRIBUTE_NAMESPACES,
                                           filter='prefix="{}"'.format(prefix))

        if cimi_resp.count == 0:
            service_attribute_namespace = self._generate_service_attribute_namespace(prefix, description, acl)
            if verbose:
                print('\nAddinging the following service attribute namespace {} ...\n{}'.format(prefix,
                                                                                                service_attribute_namespace))
            self.ssapi.cimi_add(self.RESOURCE_SERVICE_ATTRIBUTE_NAMESPACES, service_attribute_namespace)

    @staticmethod
    def _generate_service_offer(connector_instance_name, cpu, ram, root_disk, root_disk_type, os, price,
                                instance_type=None, base_currency='EUR', billing_unit='MIN', country=None,
                                platform=None, prefix=None, extra_attributes=None):
        resource_type = 'VM'
        resource_class = 'standard'

        instance_type = instance_type or ''
        instance_type_in_name = ' {}'.format(instance_type) if instance_type else ''
        instance_type_in_description = ' ({})'.format(instance_type) if instance_type else ''

        service_offer = {
            "name": "({:d}/{:d}/{:d}{} {}) [{}]".format(cpu, ram, root_disk, instance_type_in_name, os, country),
            "description": "{} ({}) with {:d} vCPU, {:d} MiB RAM, {:d} GiB root disk, {} [{}]{}"
                .format(resource_type, resource_class, cpu, ram, root_disk, os, country, instance_type_in_description),
            "resource:vcpu": cpu,
            "resource:ram": ram,
            "resource:disk": root_disk,
            "resource:diskType": root_disk_type,
            "resource:type": resource_type,
            "resource:class": resource_class,
            "resource:country": country,
            "resource:platform": platform,
            "resource:operatingSystem": os,
            "resource:instanceType": instance_type,
            "price:unitCost": price, # price  price:currency/price:unitcode
            "price:unitCode": "HUR",
            "price:freeUnits": 0,
            "price:currency": base_currency,
            "price:billingUnitCode": billing_unit, # Minimum time quantum for a resource
            "price:billingPeriodCode": "MON", # A bill is sent every billingPeriodCode
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
            if not prefix:
                raise ValueError('A prefix has to be defined with _get_prefix() to specify extra_attributes')
            for k, v in extra_attributes.items():
                service_offer['{}:{}'.format(prefix, k)] = v

        return service_offer

    def _generate_service_offers(self, connector_instance_name):
        service_offers = []

        for vm_size in self._list_vm_sizes():
            cpu = int(self._get_cpu(vm_size))
            ram = int(self._get_ram(vm_size))
            root_disk_type = self._get_root_disk_type(vm_size)
            instance_type = self._get_instance_type(vm_size)
            billing_unit = self._get_billing_unit(vm_size)
            platform = self._get_platform(vm_size)
            country = self._get_country()
            prefix = self._get_prefix()
            extra_attributes = self._get_extra_attributes(vm_size)

            if not platform and self.cc:
                platform = self.cc.cloudName

            for os in self._get_supported_os(vm_size):
                for root_disk in self._get_root_disk_sizes(vm_size, os):
                    price = None
                    raw_price, currency = self._get_price(vm_size, os, root_disk)
                    if raw_price is not None:
                        price = self.convert_currency(currency, self.base_currency, raw_price)

                    service_offers.append(self._generate_service_offer(connector_instance_name, cpu, ram, root_disk,
                                                                       root_disk_type, os, price, instance_type,
                                                                       self.base_currency, billing_unit, country,
                                                                       platform, prefix, extra_attributes))
        return service_offers

    def do_work(self):
        ch = ConfigHolder(options={'verboseLevel': 0,
                                   'retry': False,
                                   KEY_RUN_CATEGORY: ''},
                          context={'foo': 'bar'})
        self.cc = self.get_connector_class()(ch)
        self.cc._initialization(self.user_info, **self.get_initialization_extra_kwargs())

        self.base_currency = self.get_option(self.BASE_CURRENCY_KEY)

        verbose = self.get_option('verbose')
        dry_run = self.get_option(self.DRY_RUN_KEY)
        ss_endpoint = self.get_option(self.SS_ENDPOINT_KEY)
        ss_username = self.get_option(self.SS_USERNAME_KEY)
        ss_password = self.get_option(self.SS_PASSWORD_KEY)
        connector_instance_name = self.get_option(self.CONNECTOR_NAME_KEY)

        filter_connector_vm = 'connector/href="{}" and resource:type="{}"'.format(connector_instance_name, "VM")

        self.ssapi = Api(endpoint=ss_endpoint, cookie_file=None, insecure=True)
        if not dry_run:
            self.ssapi.login_internal(ss_username, ss_password)

        self._initialize()

        service_offers = self._generate_service_offers(connector_instance_name)

        if not service_offers:
            raise RuntimeError("No service offer found")

        if not dry_run and service_offers:
            self._add_service_attribute_namespace_if_not_exist('resource')
            self._add_service_attribute_namespace_if_not_exist('price')
            prefix = self._get_prefix()
            if prefix:
                self._add_service_attribute_namespace_if_not_exist(prefix)

        service_offers_ids = set()

        for service_offer in service_offers:
            if dry_run:
                print('\nService offer {}:\n{}'.format(service_offer['name'], service_offer))
            else:
                cimi_filter = '{} and description="{}"'.format(filter_connector_vm, service_offer['description'])
                search_result = self.ssapi.cimi_search('serviceOffers', filter=cimi_filter)
                result_list = search_result.resources_list
                result_count = len(result_list)

                if result_count == 0:
                    if verbose:
                        print('\nAddinging the following service offer {} to {}...\n{}'.format(service_offer['name'],
                                                                                               ss_endpoint, service_offer))

                    response = self.ssapi.cimi_add('serviceOffers', service_offer)
                    service_offers_ids.add(response.json['resource-id'])
                elif result_count == 1:
                    if verbose:
                        print('\nUpdating the following service offer {} to {}...\n{}'.format(service_offer['name'],
                                                                                              ss_endpoint, service_offer))

                    response = self.ssapi.cimi_edit(result_list[0].id, service_offer)
                    service_offers_ids.add(response.id)
                else:
                    print('\n!!! Warning duplicates found of following service offer on {} !!!\n{}'.format(ss_endpoint,
                                                                                                           service_offer['name']))
                    for result in result_list:
                        service_offers_ids.add(result.id)

        if not dry_run:
            response = self.ssapi.cimi_search('serviceOffers', filter=filter_connector_vm)
            old_service_offers_ids = set(r.id for r in response.resources())
            service_offers_ids_to_delete = old_service_offers_ids - service_offers_ids

            for id in service_offers_ids_to_delete:
                if verbose:
                    offer = self.ssapi.cimi_get(id)
                    print('\nDeleting the following service offer with id {}...\n{}'.format(id, offer.json))

                self.ssapi.cimi_delete(id)

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

