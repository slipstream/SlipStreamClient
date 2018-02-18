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
from __future__ import print_function

from collections import defaultdict

import slipstream.util as util
from slipstream.NodeDecorator import NodeDecorator


class DomExtractor(object):
    EXTRADISK_PREFIX = 'extra.disk'
    EXTRADISK_VOLATILE_KEY = EXTRADISK_PREFIX + '.volatile'

    PATH_TO_NODE_ON_RUN = 'module/nodes/entry/node'
    PATH_TO_PARAMETER = 'parameters/entry/parameter'

    @staticmethod
    def extract_nodes_instances_runtime_parameters(run_dom, cloud_service_name=None):
        """Return dict {<node_instance_name>: {<runtimeparamname>: <value>, }, }"""
        nodes_instances = {}
        for node_instance_name in run_dom.attrib['nodeNames'].split(','):
            node_instance_name = node_instance_name.strip()

            node_instance = {}
            node_instance[NodeDecorator.NODE_INSTANCE_NAME_KEY] = node_instance_name

            # Unfortunately, this doesn't work on Python < 2.7
            # query = "runtimeParameters/entry/runtimeParameter[@group='%s']" % node_instance_name
            query = "runtimeParameters/entry/runtimeParameter"
            for rtp in run_dom.findall(query):
                if rtp.get('group') == node_instance_name:
                    key = DomExtractor._get_key_from_runtimeparameter(rtp)
                    node_instance[key] = rtp.text
            nodes_instances[node_instance_name] = node_instance

        if cloud_service_name is not None:
            for node_instance_name in nodes_instances.keys():
                if cloud_service_name != nodes_instances[node_instance_name][NodeDecorator.CLOUDSERVICE_KEY]:
                    del nodes_instances[node_instance_name]

        return nodes_instances

    @staticmethod
    def extract_nodes_runtime_parameters(run_dom):
        """Return dict {<node_name>: {<runtimeparamname>: <value>, }, }"""
        nodes = {}
        node_names = DomExtractor._get_node_names(run_dom)

        for node_name in node_names:
            node = {}
            node[NodeDecorator.NODE_NAME_KEY] = node_name

            # Unfortunately, this doesn't work on Python < 2.7
            # query = "runtimeParameters/entry/runtimeParameter[@group='%s']" % node_instance_name
            query = "runtimeParameters/entry/runtimeParameter"
            for rtp in run_dom.findall(query):
                if rtp.get('group') == node_name:
                    key = DomExtractor._get_key_from_runtimeparameter(rtp)
                    node[key] = rtp.text
            nodes[node_name] = node

        return nodes

    @staticmethod
    def _get_node_names(run_dom):
        """Return list of node names in the run."""
        node_names = []
        for group in run_dom.attrib['groups'].split(','):
            node_name = ""
            try:
                node_name = group.split(NodeDecorator.NODE_PROPERTY_SEPARATOR)[1]
            except IndexError:
                pass
            else:
                node_names.append(node_name.strip())
        return node_names

    @staticmethod
    def _get_key_from_runtimeparameter(rtp):
        return rtp.attrib['key'].split(NodeDecorator.NODE_PROPERTY_SEPARATOR, 1)[-1]

    @staticmethod
    def extract_node_image_attributes(run_dom, nodename):
        """Return image attributes of all nodes."""
        image = DomExtractor.extract_node_image(run_dom, nodename)
        attributes = {}

        if image is not None:
            attributes = DomExtractor.get_attributes(image)

        return attributes

    @staticmethod
    def extract_node_image(run_dom, nodename):
        """Return image attributes of all nodes."""
        image = None

        if DomExtractor.get_module_category(run_dom) == NodeDecorator.IMAGE:
            image = run_dom.find('module')
        else:
            for node in run_dom.findall(DomExtractor.PATH_TO_NODE_ON_RUN):
                if node.get('name') == nodename:
                    image = node.find('image')

        return image

    @staticmethod
    def extract_deployment(run_dom, nodename):
        """Return the deployment module of a run."""
        return run_dom.find('module')

    @staticmethod
    def extract_node_image_targets(run_dom, node_name):

        if NodeDecorator.is_orchestrator_name(node_name):
            module_dom = DomExtractor.extract_deployment(run_dom, node_name)
        else:
            module_dom = DomExtractor.extract_node_image(run_dom, node_name)

        return DomExtractor.get_targets_from_module(module_dom)

    @staticmethod
    def extract_node_image_build_state(run_dom, node_name):

        if NodeDecorator.is_orchestrator_name(node_name):
            return {}

        image_dom = DomExtractor.extract_node_image(run_dom, node_name)
        return DomExtractor.get_build_state_from_image(image_dom)

    @staticmethod
    def get_build_state_from_image(image_dom):
        build_state = {}

        for st in image_dom.findall('buildStates/buildState'):
            module_uri = st.get('moduleUri')
            built_on = st.get('builtOn', '').split(',')
            build_state[module_uri] = dict(module_uri=module_uri, built_on=built_on)

        return build_state

    @staticmethod
    def get_module_category(run_dom):
        module = run_dom.find('module')
        return module.get('category', None) if module is not None else None

    @staticmethod
    def get_extra_disks_from_image(image_dom):
        extra_disks = {}

        for entry in image_dom.findall('parameters/entry'):
            param_name = entry.find('parameter').get('name')
            if param_name.startswith(DomExtractor.EXTRADISK_PREFIX):
                try:
                    extra_disks[param_name] = entry.find('parameter/value').text or ''
                except AttributeError:
                    pass

        return extra_disks

    @staticmethod
    def get_element_value_from_element_tree(element_tree, element_name):
        element = element_tree.find(element_name)
        value = getattr(element, 'text', '')
        if value is None:
            value = ''
        return value

    @staticmethod
    def get_attributes(dom):
        return dom.attrib

    @staticmethod
    def get_packages(module_dom):
        packages = []

        for package in module_dom.findall('packagesExpanded/packageExpanded'):
            name = package.get('name')
            if name:
                packages.append(name)

        return packages

    @staticmethod
    def extractCategoryFromRun(run_dom):
        return run_dom.attrib['category']

    @staticmethod
    def extractTypeFromRun(run_dom):
        return run_dom.attrib['type']

    @staticmethod
    def extract_mutable_from_run(run_dom):
        return run_dom.attrib[util.RUN_PARAM_MUTABLE]

    @staticmethod
    def extractDefaultCloudServiceNameFromRun(run_dom):
        return run_dom.attrib['cloudServiceName']

    @staticmethod
    def extract_run_parameters_from_run(run_dom):
        parameters = {}
        for node in run_dom.findall(DomExtractor.PATH_TO_PARAMETER):
            value = node.find('value')
            parameters[node.get('name')] = value.text if value is not None else None
        return parameters

    @staticmethod
    def get_targets_from_module(module_dom):
        """Return deployment targets of the given image."""
        targets = {}
        for st in module_dom.findall('targetsExpanded/targetExpanded/subTarget'):
            name = st.get('name')
            subtarget = dict(name=name,
                             order=int(st.get('order')),
                             module_uri=st.get('moduleUri'),
                             module=st.get('moduleShortName'),
                             script=st.text)

            targets.setdefault(name, [])
            targets[name].append(subtarget)

        for target in targets.itervalues():
            target.sort(key=lambda t: t.get('order'))

        if module_dom.tag == "imageModule" or module_dom.tag == "image" \
                or module_dom.get('category') == NodeDecorator.IMAGE:
            targets[NodeDecorator.NODE_PACKAGES] = DomExtractor.get_packages(module_dom)

        return targets

    @staticmethod
    def server_config_dom_into_dict(config_dom, categories=[], value_updater=None):
        """
        :param config_dom: Element Tree representation of the server's configuration.
        :param categories: categories to extract; if empty, extracts all categories.
        :return: dictionary {'category': [('param', 'value'),],}
        """
        config = defaultdict(list)
        for param in config_dom.findall('parameters/entry'):
            category = param.find('parameter').get('category')
            if categories and (category not in categories):
                continue
            name = param.find('parameter').get('name')
            value = param.find('parameter/value').text
            if value is None:
                value = ''
            if '\n' in value:
                value = value.replace('\n', '')
            if hasattr(value_updater, '__call__'):
                value = value_updater(value)
            config[category].append((name, value))
        return config
