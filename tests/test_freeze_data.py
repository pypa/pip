from StringIO import StringIO
from path import Path
from tests.test_pip import reset_env
from tests.test_pip import run_pip
from tests.test_pip import write_file
from unittest import TestCase
import textwrap


class ns(object):
    env = None


def setup():
    ns.env = reset_env()
    write_file('initools-req.txt', textwrap.dedent("""\
        INITools==0.2
        # and something else to test out:
        MarkupSafe<=0.12
        """))
    run_pip('install', '-r', ns.env.scratch_path/'initools-req.txt')


class TestFreezeData(TestCase):
    
    def setUp(self):
        self.env_sp = ns.env.venv_path / 'lib/python2.7/site-packages'
        self.io = StringIO()
        
    def make_one(self, **kw):
        kw['handle'] = kw.get('handle') or self.io
        kw['working_set_entries'] = kw.get('working_set_entries') or [self.env_sp]
        from pip.data import FreezeData
        data = FreezeData(**kw)
        return data

    def test_freezedata_init(self):
        """
        dumb test to assert coverage
        """
        data = self.make_one()
        assert len(data) == 0
        assert len([x for x in data.working_set]) == 2, "Environment issue"

    def test_freezedata_asdict(self):
        data = self.make_one()
         # should be ignored
        assert data.as_dict
        assert len(data.load_installed()) == 2
        data.insert(0, '# a comment')
        assert set(data.as_dict['requirements'].keys()) == set(('INITools', 'MarkupSafe'))
        data.append('-i http://pkg-index')
        assert data.as_dict['indexes'] == ['http://pkg-index']

    def test_load_all(self):
        from pip.data import FreezeData
        data = FreezeData.load_all(handle=self.io, working_set_entries=[self.env_sp])
        assert len(data) == 2
        assert self.io.getvalue() == 'INITools==0.2\nMarkupSafe==0.12\n'

    def test_w_requirement_file(self):
        """
        pip freeze can take a requirements file as a "hint".  
        """
        other_lib_name, other_lib_version = 'anyjson', '0.3'
        write_file('initools-req.txt',
                   textwrap.dedent("""
                   -i http://pkg-index
                   INITools==0.2
                   # and something else to test out:
                   %s<=%s
                   """ % (other_lib_name, other_lib_version)))
        data = self.make_one(handle=self.io)
        data.load_installed(ns.env.scratch_path / 'initools-req.txt')
        assert not "# and something else to test out:" in data
        assert '-i http://pkg-index' in data
        assert 'INITools==0.2' == data[1].strip()

    def test_w_requirement_file_skip_arg(self):
        """
        If a skip arg is used, the flag should still be output, but
        the INITools package should now be added by pip.
        """
        other_lib_name, other_lib_version = 'anyjson', '0.3'
        write_file('initools-req.txt',
                   textwrap.dedent("""\
                   -i http://pkg-index
                   INITools==0.2
                   # and something else to test out:
                   %s<=%s
                   """ % (other_lib_name, other_lib_version)))
        data = self.make_one(handle=self.io)
        regex = r'^INI.*'
        data.load_installed(ns.env.scratch_path / 'initools-req.txt', skip_requirements_regex=regex)
        assert '-i http://pkg-index' == data[0].strip()
        assert 'INITools==0.2' == data[2].strip()
        
    def test_dependency_links_metadata(self):
        data = self.make_one()
        adist = next(iter(data.working_set))
        deplinks = Path(adist.egg_info) / 'dependency_links.txt'
        link = 'http://happyindex/pkg.101.tar.gz#egg=pkg'
        deplinks_fh = open(deplinks, 'w')
        deplinks_fh.write(link)
        deplinks_fh.write('\n')
        deplinks_fh.close()
        data = self.make_one()
        assert data.dependency_links == [link]
        deplinks.rm()

    def test_dependency_links_noargs(self):
        data = self.make_one()
        assert data.dependency_links == []

    def test_dependency_links_w_findlinks(self):
        find_links=['http://happyindex/pkg.101.tar.gz#egg=pkg']
        data = self.make_one(find_links=find_links)
        assert data.dependency_links == find_links

    def test_text_output(self):
        data = self.make_one(handle=self.io, write_on_load=False)
        data.write_output()
        assert not self.io.getvalue()
        data.load_installed()
        data.write_output()
        assert self.io.getvalue() == 'INITools==0.2\nMarkupSafe==0.12\n'        


