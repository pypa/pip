import json
from pip.log import logger


class ListCommand:
    def output(self, text):
        logger.notify(text)

    def outdated_item(self, **keys):
        raise NotImplementedError

    def package_list_item(self, project_name,
          version, location=None):
        if location:
          self.package_list_with_location(project_name, version, location)
        else:
          self.package_list_without_location(project_name, version)

    def package_list_without_location(self, project_name, version):
        raise NotImplementedError

    def package_list_with_location(self, project_name, version, location):
        raise NotImplementedError

    def output_end(self):
        pass


class TextFormat(ListCommand):
    format_type = 'text'

    def outdated_item(self, project_name, current_version, latest_version):
        self.output('%s (Current: %s Latest: %s)' % (project_name,
                    current_version, latest_version))

    def package_list_with_location(self, project_name, version, location):
        self.output('%s (%s, %s)' % (project_name, version, location))

    def package_list_without_location(self, project_name, version):
        self.output('%s (%s)' % (project_name, version))


class JsonFormat(ListCommand):
    format_type = 'json'

    def __init__(self):
        self.items = []

    def outdated_item(self, project_name, current_version, latest_version):
        self.items.append({
            'package': project_name,
            'current': current_version,
            'latest': latest_version
        })

    def package_list_with_location(self, project_name, version, location):
        self.items.append({
            'package': project_name,
            'version': version,
            'location': location
        })

    def package_list_without_location(self, project_name, version):
      self.package_list_with_location(project_name, version, None)

    def output_end(self):
        self.output(json.dumps(self.items))


class CsvFormat(ListCommand):
    format_type = 'csv'

    def __init__(self):
        self.printed_header = False

    def outdated_item(self, project_name, current_version, latest_version):
        if not self.printed_header:
            self.output('Package,CurrentVersion,LatestVersion')
            self.printed_header = True
        self.output(','.join([project_name, current_version, latest_version]))

    def package_list_with_location(self, project_name, version, location):
        self._print_header_for_package_listing()
        self.output(','.join([project_name, version, location]))

    def package_list_without_location(self, project_name, version):
        self.package_list_with_location(project_name, version, '')

    def _print_header_for_package_listing(self):
        if not self.printed_header:
            self.output('Package,Version,Location')
            self.printed_header = True
