#!/usr/bin/env python
# encoding: utf-8

'''
Version information constants and auxiliary functions.
'''


# If you change this version, change it also in docs/conf.py
VERSION = (1, 0, 2, 'post1')


import os, sys
import subprocess as sub

__here__ = os.path.abspath(os.path.dirname(__file__))


def _check_output(*cmd):
    p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE, cwd=__here__)
    return p.communicate()[0].rstrip('\n')


# PEP8 hates me
_gitsha = lambda : _check_output('git', 'rev-parse',    'HEAD')
_gitbrc = lambda : _check_output('git', 'symbolic-ref', 'HEAD').replace('refs/heads/', '')


def version():
    return '.'.join([str(i) for i in VERSION])


def version_verbose():
    res = 'pip %s' % version()
    try:
        sha = _gitsha() ; brc = _gitbrc()
        res = '%s (%s:%s)' % (res, brc, sha[:8])
    except:
        pass

    return res

def version_dist_verbose():
    from pkg_resources import get_distribution, DistributionNotFound

    try:
        pip_dist = get_distribution('pip')
        version = '%s from %s (python %s)' % (
            pip_dist, pip_dist.location, sys.version[:3])

        return version
    except DistributionNotFound:
        # when running pip.py without installing
        return version_verbose()


__all__ = (VERSION, version, version_verbose, version_dist_verbose)


if __name__ == '__main__':
    print version_verbose()
