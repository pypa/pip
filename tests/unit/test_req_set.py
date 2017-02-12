from pip.req.req_install import InstallRequirement
from pip.req.req_set import RequirementSet
import mock


class TestRequirementSet(object):

    @mock.patch('pip.req.req_set.get_installed_distributions')
    @mock.patch('pip.req.req_install.ask')
    def test_uninstall(self, mock_ask, mock_distributions):
        mock_ask.return_value = 'y'
        mock_distributions.return_value = [
            mock.Mock(requires=lambda: [mock.Mock(key="dummy")]),
        ]

        class session(object):
            pass

        class req(object):
            def __init__(self, name):
                self.name = name

        class installed(InstallRequirement):
            def __init__(self, name, link=None, constraint=False):
                self.req = req(name)
                self.link = link
                self.constraint = constraint
                self.uninstalled_pathset = mock.MagicMock()

            def check_if_exists(self):
                return True

            def match_markers(self, *args, **kwargs):
                return True

            def uninstall(self, auto_confirm=False):
                pass

        req_set = RequirementSet(None, None, None, session=session())
        req_set.add_requirement(
            installed(
                "dummy",
            )
        )
        req_set.uninstall()
        mock_ask.assert_called_with('Proceed (y/n)? ', ('y', 'n'))
