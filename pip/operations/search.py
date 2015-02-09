# The guts of search

from pip.download import PipXmlrpcTransport
from pip._vendor.six.moves import xmlrpc_client
from pip._vendor import pkg_resources


def search(query, index_url, session):
    transport = PipXmlrpcTransport(index_url, session)
    pypi = xmlrpc_client.ServerProxy(index_url, transport)
    hits = pypi.search({'name': query, 'summary': query}, 'or')
    return hits


def transform_hits(hits):
    """
    The list from pypi is really a list of versions. We want a list of
    packages with the list of versions stored inline. This converts the
    list from pypi into one we can use.
    """
    packages = {}
    for hit in hits:
        name = hit['name']
        summary = hit['summary']
        version = hit['version']
        score = hit['_pypi_ordering']
        if score is None:
            score = 0

        if name not in packages.keys():
            packages[name] = {
                'name': name,
                'summary': summary,
                'versions': [version],
                'score': score,
            }
        else:
            packages[name]['versions'].append(version)

            # if this is the highest version, replace summary and score
            if version == highest_version(packages[name]['versions']):
                packages[name]['summary'] = summary
                packages[name]['score'] = score

    # each record has a unique name now, so we will convert the dict into a
    # list sorted by score
    package_list = sorted(
        packages.values(),
        key=lambda x: x['score'],
        reverse=True,
    )
    return package_list


def highest_version(versions):
    return next(iter(
        sorted(versions, key=pkg_resources.parse_version, reverse=True)
    ))
