import pytest
from pip._vendor.packaging.tags import Tag

from pip._internal.exceptions import InvalidWheelFilename
from pip._internal.models.wheel import Wheel
from pip._internal.utils import compatibility_tags


class TestWheelFile:
    def test_std_wheel_pattern(self):
        w = Wheel("simple-1.1.1-py2-none-any.whl")
        assert w.name == "simple"
        assert w.version == "1.1.1"
        assert w.pyversions == ["py2"]
        assert w.abis == ["none"]
        assert w.plats == ["any"]

    def test_wheel_pattern_multi_values(self):
        w = Wheel("simple-1.1-py2.py3-abi1.abi2-any.whl")
        assert w.name == "simple"
        assert w.version == "1.1"
        assert w.pyversions == ["py2", "py3"]
        assert w.abis == ["abi1", "abi2"]
        assert w.plats == ["any"]

    def test_wheel_with_build_tag(self):
        # pip doesn't do anything with build tags, but theoretically, we might
        # see one, in this case the build tag = '4'
        w = Wheel("simple-1.1-4-py2-none-any.whl")
        assert w.name == "simple"
        assert w.version == "1.1"
        assert w.pyversions == ["py2"]
        assert w.abis == ["none"]
        assert w.plats == ["any"]

    def test_single_digit_version(self):
        w = Wheel("simple-1-py2-none-any.whl")
        assert w.version == "1"

    def test_non_pep440_version(self):
        w = Wheel("simple-_invalid_-py2-none-any.whl")
        assert w.version == "-invalid-"

    def test_missing_version_raises(self):
        with pytest.raises(InvalidWheelFilename):
            Wheel("Cython-cp27-none-linux_x86_64.whl")

    def test_invalid_filename_raises(self):
        with pytest.raises(InvalidWheelFilename):
            Wheel("invalid.whl")

    def test_supported_single_version(self):
        """
        Test single-version wheel is known to be supported
        """
        w = Wheel("simple-0.1-py2-none-any.whl")
        assert w.supported(tags=[Tag("py2", "none", "any")])

    def test_supported_multi_version(self):
        """
        Test multi-version wheel is known to be supported
        """
        w = Wheel("simple-0.1-py2.py3-none-any.whl")
        assert w.supported(tags=[Tag("py3", "none", "any")])

    def test_not_supported_version(self):
        """
        Test unsupported wheel is known to be unsupported
        """
        w = Wheel("simple-0.1-py2-none-any.whl")
        assert not w.supported(tags=[Tag("py1", "none", "any")])

    def test_supported_osx_version(self):
        """
        Wheels built for macOS 10.6 are supported on 10.9
        """
        tags = compatibility_tags.get_supported(
            "27", platforms=["macosx_10_9_intel"], impl="cp"
        )
        w = Wheel("simple-0.1-cp27-none-macosx_10_6_intel.whl")
        assert w.supported(tags=tags)
        w = Wheel("simple-0.1-cp27-none-macosx_10_9_intel.whl")
        assert w.supported(tags=tags)

    def test_not_supported_osx_version(self):
        """
        Wheels built for macOS 10.9 are not supported on 10.6
        """
        tags = compatibility_tags.get_supported(
            "27", platforms=["macosx_10_6_intel"], impl="cp"
        )
        w = Wheel("simple-0.1-cp27-none-macosx_10_9_intel.whl")
        assert not w.supported(tags=tags)

    @pytest.mark.xfail(
        reason=(
            "packaging.tags changed behaviour in this area, and @pradyunsg "
            "decided as the release manager that this behaviour change is less "
            "critical than Big Sur support for pip 20.3. See "
            "https://github.com/pypa/packaging/pull/361 for further discussion."
        )
    )
    def test_supported_multiarch_darwin(self):
        """
        Multi-arch wheels (intel) are supported on components (i386, x86_64)
        """
        universal = compatibility_tags.get_supported(
            "27", platforms=["macosx_10_5_universal"], impl="cp"
        )
        intel = compatibility_tags.get_supported(
            "27", platforms=["macosx_10_5_intel"], impl="cp"
        )
        x64 = compatibility_tags.get_supported(
            "27", platforms=["macosx_10_5_x86_64"], impl="cp"
        )
        i386 = compatibility_tags.get_supported(
            "27", platforms=["macosx_10_5_i386"], impl="cp"
        )
        ppc = compatibility_tags.get_supported(
            "27", platforms=["macosx_10_5_ppc"], impl="cp"
        )
        ppc64 = compatibility_tags.get_supported(
            "27", platforms=["macosx_10_5_ppc64"], impl="cp"
        )

        w = Wheel("simple-0.1-cp27-none-macosx_10_5_intel.whl")
        assert w.supported(tags=intel)
        assert w.supported(tags=x64)
        assert w.supported(tags=i386)
        assert not w.supported(tags=universal)
        assert not w.supported(tags=ppc)
        assert not w.supported(tags=ppc64)
        w = Wheel("simple-0.1-cp27-none-macosx_10_5_universal.whl")
        assert w.supported(tags=universal)
        assert w.supported(tags=intel)
        assert w.supported(tags=x64)
        assert w.supported(tags=i386)
        assert w.supported(tags=ppc)
        assert w.supported(tags=ppc64)

    def test_not_supported_multiarch_darwin(self):
        """
        Single-arch wheels (x86_64) are not supported on multi-arch (intel)
        """
        universal = compatibility_tags.get_supported(
            "27", platforms=["macosx_10_5_universal"], impl="cp"
        )
        intel = compatibility_tags.get_supported(
            "27", platforms=["macosx_10_5_intel"], impl="cp"
        )

        w = Wheel("simple-0.1-cp27-none-macosx_10_5_i386.whl")
        assert not w.supported(tags=intel)
        assert not w.supported(tags=universal)
        w = Wheel("simple-0.1-cp27-none-macosx_10_5_x86_64.whl")
        assert not w.supported(tags=intel)
        assert not w.supported(tags=universal)

    def test_support_index_min(self):
        """
        Test results from `support_index_min`
        """
        tags = [
            Tag("py2", "none", "TEST"),
            Tag("py2", "TEST", "any"),
            Tag("py2", "none", "any"),
        ]
        w = Wheel("simple-0.1-py2-none-any.whl")
        assert w.support_index_min(tags=tags) == 2
        w = Wheel("simple-0.1-py2-none-TEST.whl")
        assert w.support_index_min(tags=tags) == 0

    def test_support_index_min__none_supported(self):
        """
        Test a wheel not supported by the given tags.
        """
        w = Wheel("simple-0.1-py2-none-any.whl")
        with pytest.raises(ValueError):
            w.support_index_min(tags=[])

    def test_version_underscore_conversion(self):
        """
        Test that we convert '_' to '-' for versions parsed out of wheel
        filenames
        """
        w = Wheel("simple-0.1_1-py2-none-any.whl")
        assert w.version == "0.1-1"
