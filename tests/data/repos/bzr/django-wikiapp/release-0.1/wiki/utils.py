# -*- coding: utf-8 -*-
""" Some util functions.
"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required as _login_required


def get_ct(obj):
    """ Return the ContentType of the object's model.
    """
    return ContentType.objects.get(app_label=obj._meta.app_label,
                                   model=obj._meta.module_name)

def login_required(function):
    if getattr(settings, 'WIKI_REQUIRES_LOGIN', False):
        return _login_required(function)
    return function
