# -*- coding: utf-8 -*-
""" Provides the `creole` template filter, to render
texts using the markup used by the MoinMoin wiki.
"""

from django import template
from django.conf import settings

try:
    from creoleparser.dialects import Creole10 as Creole
    from creoleparser.core import Parser as CreoleParser
    # create it only once, because it is fairly expensive
    # (e.g., all the regular expressions it uses are compiled)
    dialect = Creole(use_additions=True)
except ImportError:
    Creole = None


register = template.Library()


@register.filter
def creole(text, **kw):
    """Returns the text rendered by the Creole markup.
    """
    if Creole is None and settings.DEBUG:
        raise template.TemplateSyntaxError("Error in creole filter: "
            "The Creole library isn't installed, try easy_install Creoleparser.")
    parser = CreoleParser(dialect=dialect)
    return parser.render(text)

class CreoleTextNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        return creole(self.nodelist.render(context))

@register.tag("creole")
def crl_tag(parser, token):
    """
    Render the Creole into html. Will pre-render template code first.
    """
    nodelist = parser.parse(('endcreole',))
    parser.delete_first_token()
    return CreoleTextNode(nodelist)

