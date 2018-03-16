import sys

# This code exists for backwards compatibility reasons.
# I don't like it either. Just look the other way. :)

for package in ('urllib3', 'idna', 'chardet'):
    locals()[package] = __import__("pip._vendor." + package)
    # This traversal is apparently necessary such that the identities are
    # preserved (requests.packages.urllib3.* is urllib3.*)
    for mod in list(sys.modules):
        if mod == package or mod.startswith(package + '.'):
            sys.modules['pip._vendor.requests.packages.' + mod] = sys.modules["pip._vendor." + mod]

# Kinda cool, though, right?
