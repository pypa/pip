from setuptools import setup, find_packages

setup(
    name = "plugin",
    version = '1.0',
    packages=find_packages(),
    entry_points = {'pip.commands': ['command = plugin:PluginCommand']}
)


