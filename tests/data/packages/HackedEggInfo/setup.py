from setuptools import setup
from setuptools.command import egg_info as orig_egg_info


class egg_info(orig_egg_info.egg_info):
    def run(self):
        orig_egg_info.egg_info.run(self)


setup(
    name="hackedegginfo",
    version="0.0.0",
    cmdclass={"egg_info": egg_info},
    zip_safe=False,
)
