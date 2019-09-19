"""Metadata generation logic for source distributions.
"""


def get_metadata_generator(install_req):
    if not install_req.use_pep517:
        return install_req.run_egg_info

    return install_req.prepare_pep517_metadata
