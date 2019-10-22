import pytest
from mock import Mock, call, patch

from pip._internal.commands.install import build_wheels, decide_user_install


class TestWheelCache:

    def check_build_wheels(
        self,
        pep517_requirements,
        legacy_requirements,
    ):
        """
        Return: (mock_calls, return_value).
        """
        def build(reqs, **kwargs):
            # Fail the first requirement.
            return [reqs[0]]

        builder = Mock()
        builder.build.side_effect = build

        build_failures = build_wheels(
            builder=builder,
            pep517_requirements=pep517_requirements,
            legacy_requirements=legacy_requirements,
        )

        return (builder.build.mock_calls, build_failures)

    @patch('pip._internal.commands.install.is_wheel_installed')
    def test_build_wheels__wheel_installed(self, is_wheel_installed):
        is_wheel_installed.return_value = True

        mock_calls, build_failures = self.check_build_wheels(
            pep517_requirements=['a', 'b'],
            legacy_requirements=['c', 'd'],
        )

        # Legacy requirements were built.
        assert mock_calls == [
            call(['a', 'b'], should_unpack=True),
            call(['c', 'd'], should_unpack=True),
        ]

        # Legacy build failures are not included in the return value.
        assert build_failures == ['a']

    @patch('pip._internal.commands.install.is_wheel_installed')
    def test_build_wheels__wheel_not_installed(self, is_wheel_installed):
        is_wheel_installed.return_value = False

        mock_calls, build_failures = self.check_build_wheels(
            pep517_requirements=['a', 'b'],
            legacy_requirements=['c', 'd'],
        )

        # Legacy requirements were not built.
        assert mock_calls == [
            call(['a', 'b'], should_unpack=True),
        ]

        assert build_failures == ['a']


class TestDecideUserInstall:
    @patch('site.ENABLE_USER_SITE', True)
    @patch('pip._internal.commands.install.site_packages_writable')
    def test_prefix_and_target(self, sp_writable):
        sp_writable.return_value = False

        assert decide_user_install(
            use_user_site=None, prefix_path='foo'
        ) is False

        assert decide_user_install(
            use_user_site=None, target_dir='bar'
        ) is False

    @pytest.mark.parametrize(
        "enable_user_site,site_packages_writable,result", [
            (True, True, False),
            (True, False, True),
            (False, True, False),
            (False, False, False),
        ])
    def test_most_cases(
        self, enable_user_site, site_packages_writable, result, monkeypatch,
    ):
        monkeypatch.setattr('site.ENABLE_USER_SITE', enable_user_site)
        monkeypatch.setattr(
            'pip._internal.commands.install.site_packages_writable',
            lambda **kw: site_packages_writable
        )
        assert decide_user_install(use_user_site=None) is result
