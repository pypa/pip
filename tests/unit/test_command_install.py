from mock import Mock, call, patch

from pip._internal.commands.install import build_wheels


class TestWheelCache:

    def check_build_wheels(
        self,
        pep517_requirements,
        legacy_requirements,
        session,
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
            # A session value isn't needed.
            session='<session>',
            options='<options>'
        )

        return (builder.build.mock_calls, build_failures)

    @patch('pip._internal.commands.install.should_build_legacy')
    def test_build_wheels__should_build_legacy_true(self, should_build_legacy):
        should_build_legacy.return_value = True

        mock_calls, build_failures = self.check_build_wheels(
            pep517_requirements=['a', 'b'],
            legacy_requirements=['c', 'd'],
            session='<session>',
        )

        # Legacy requirements were built.
        assert mock_calls == [
            call(['a', 'b'], autobuilding=True, session='<session>'),
            call(['c', 'd'], autobuilding=True, session='<session>'),
        ]

        # Legacy build failures are not included in the return value.
        assert build_failures == ['a']

    @patch('pip._internal.commands.install.should_build_legacy')
    def test_build_wheels__should_build_legacy_false(
        self, should_build_legacy,
    ):
        should_build_legacy.return_value = False

        mock_calls, build_failures = self.check_build_wheels(
            pep517_requirements=['a', 'b'],
            legacy_requirements=['c', 'd'],
            session='<session>',
        )

        # Legacy requirements were not built.
        assert mock_calls == [
            call(['a', 'b'], autobuilding=True, session='<session>'),
        ]

        assert build_failures == ['a']
