from mock import Mock, call, patch

from pip._internal.commands.install import build_wheels


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
            call(['a', 'b'], autobuilding=True),
            call(['c', 'd'], autobuilding=True),
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
            call(['a', 'b'], autobuilding=True),
        ]

        assert build_failures == ['a']
