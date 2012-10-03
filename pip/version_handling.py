from distutils.version import StrictVersion, LooseVersion
__all__ = ['highest_version']

def compare_versions(version1, version2):
    try:
        return cmp(StrictVersion(version1), StrictVersion(version2))
    # in case of abnormal version number, fall back to LooseVersion
    except ValueError:
        pass
    try:
        return cmp(LooseVersion(version1), LooseVersion(version2))
    except TypeError:
    # certain LooseVersion comparions raise due to unorderable types,
    # fallback to string comparison
        return cmp([str(v) for v in LooseVersion(version1).version],
                   [str(v) for v in LooseVersion(version2).version])


def highest_version(versions):
    return reduce((lambda v1, v2: compare_versions(v1, v2) == 1 and v1 or v2), versions)



