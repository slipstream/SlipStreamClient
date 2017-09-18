#!/usr/bin/env python
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
from __future__ import print_function

import os
import os.path
import re
import xml.etree.ElementTree as ET

from slipstream.command.ModuleCommand import ModuleCommand


class ModuleDownloadCommand(ModuleCommand):
    """Recursively download SlipStream modules as XML from server."""

    def __init__(self):
        super(ModuleDownloadCommand, self).__init__()

    @staticmethod
    def _remove_element(parent, element):
        if element is not None:
            parent.remove(element)

    @classmethod
    def _remove_transient_elements(cls, root):
        cls._remove_element(root, root.find('inputParametersExpanded'))
        cls._remove_element(root, root.find('packagesExpanded'))
        cls._remove_element(root, root.find('targetsExpanded'))
        cls._remove_element(root, root.find('buildStates'))
        cls._remove_element(root, root.find('runs'))

    @staticmethod
    def _remove_clouds(root):
        """Remove the cloudImageIdentifiers, cloudNames and cloud specific
        parameters element from the given document. These elements are not
        portable between SlipStream deployments."""

        ids = root.find('cloudImageIdentifiers')
        if ids is not None:
            for id in ids.findall('*'):
                ids.remove(id)

        cloud_names = root.find('cloudNames')
        if cloud_names is not None:
            cloud_names.attrib['length'] = '0'
            parameters = root.find('parameters')
            if parameters is not None:
                for cloud_name in cloud_names.findall('*'):
                    cloud_parameters = parameters.findall("./entry/parameter[@category='%s'].." % cloud_name.text)
                    if cloud_parameters is not None:
                        for cloud_parameter in cloud_parameters:
                            parameters.remove(cloud_parameter)
                        cloud_names.remove(cloud_name)

    @staticmethod
    def _remove_group_members(root):
        authz = root.find('authz')
        if authz is None:
            return

        group_members = authz.find('groupMembers')
        if group_members is None:
            return

        for group_member in group_members.findall('*'):
            group_members.remove(group_member)

    @staticmethod
    def _reset_commit_message(root):
        authz = root.find('authz')

        commit = root.find('commit')
        if commit is None:
            return

        commit.attrib['author'] = (authz is not None) and authz.attrib.get('owner', 'super') or 'super'

        comment = commit.find('comment')
        if comment is None:
            return
        comment.text = 'Initial version of this module'

    @staticmethod
    def _write_module_as_xml(root_element, module, flat_export=False):
        if flat_export:
            module = module.replace('/', '_')
        else:
            if root_element.attrib.get('category', '').lower().strip() == 'project':
                module = os.path.join(module, os.path.basename(module))
            try:
                os.makedirs(os.path.dirname(module), 0o775)
            except OSError as e:
                pass
        ET.ElementTree(root_element).write('%s.xml' % module)

    @staticmethod
    def _get_module_children(module, root_element):
        children = []
        for child in root_element.findall('children/item'):
            module_name = child.attrib['name']
            module_path = '%s/%s' % (module, module_name)
            children.append(module_path)
        return children

    @staticmethod
    def _is_image(root):
        return root.tag == 'imageModule'

    @staticmethod
    def _dump_image_ids(root, dump_image_ids_dir):
        ids = root.find('cloudImageIdentifiers')
        if ids is not None:
            module_name = root.get('shortName')
            module_path = re.sub('^module/', '', root.get('parentUri'))
            module_uri = "%s/%s" % (module_path, module_name)
            cloud_ids = ''
            for _id in ids.findall('*'):
                cloud_ids += "%s = %s:%s\n" % (module_uri, _id.get('cloudServiceName'),
                                               _id.get('cloudImageIdentifier'))
            if cloud_ids:
                if not os.path.exists(dump_image_ids_dir):
                    os.makedirs(dump_image_ids_dir)
                fn = '%s_%s' % (module_path.replace('/','_'), module_name)
                ids_file = "%s/%s.conf" % (dump_image_ids_dir, fn)
                with open(ids_file, 'w') as fh:
                    fh.write(cloud_ids)

    def _retrieve_module_as_xml(self, uri):
        xml_str = self.module_get(uri)
        return ET.fromstring(xml_str)

