from slipstream.DomExtractor import DomExtractor
from slipstream.api.module import Module
from .CommandBase import CommandBase


class ModuleCommand(CommandBase):

    def __init__(self):
        self.module_uri = ''
        self.module_xml = ''
        self.cookie = None
        self._module = None
        self.force = False
        super(ModuleCommand, self).__init__()

    @property
    def module(self):
        if not self._module:
            self._module = Module(self.cimi)
        return self._module

    def module_delete(self, uri):
        return self.module.delete(uri)

    def module_get(self, uri):
        return self.module.get(uri)

    def module_create(self, module_str):
        _, uri = self._dom_and_uri_from_xml_str(module_str)
        return self.module.edit(uri, module_str)

    def _dom_and_uri_from_xml_str(self, module_str):
        dom, attrs = self._module_parse_xml(module_str)

        root_node_name = dom.tag
        if root_node_name == 'list':
            self._exit('Cannot update root project.')
        if dom.tag not in ('imageModule', 'projectModule', 'deploymentModule'):
            self._exit('Invalid xml.')

        parts = [attrs['parentUri'], attrs['shortName']]
        uri = '/' + '/'.join([part.strip('/') for part in parts])
        return dom, uri

    def _module_parse_xml(self, module_str):
        dom = self.parse_xml_or_exit_on_error(module_str)
        attrs = DomExtractor.get_attributes(dom)
        return dom, attrs

    def _put(self, uri, fn):
        with open(fn) as f:
            try:
                self.module.edit(uri, f.read())
            except:
                if self.force is not True:
                    raise

    def modules_upload(self):
        # read all files once to determine the upload URL for each file
        # the URL is used to sort the files into an order that puts
        # parents before children
        projects = {}
        images = {}
        deployments = {}
        for fn in self.args:
            self.check_is_file(fn)
            with open(fn) as f:
                dom, uri = self._dom_and_uri_from_xml_str(f.read())
                if dom.tag == 'projectModule':
                    projects[uri] = fn
                elif dom.tag == 'imageModule':
                    images[uri] = fn
                elif dom.tag == 'deploymentModule':
                    deployments[uri] = fn

        # now actually do the uploads in the correct order
        # projects must be done first to get the structure, then
        # images, and finally the deployments
        for url in sorted(projects):
            fn = projects[url]
            print('Uploading project: %s' % fn)
            self._put(url, fn)

        for url in sorted(images):
            fn = images[url]
            print('Uploading image: %s' % fn)
            self._put(url, fn)

        for url in sorted(deployments):
            fn = deployments[url]
            print('Uploading deployment: %s' % fn)
            self._put(url, fn)
