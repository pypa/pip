# -*- coding: utf-8 -*-

from django.template import Node, Library, TemplateSyntaxError
from django.core.urlresolvers import reverse, NoReverseMatch

register = Library()

class WikiURLNode(Node):
    def __init__(self, url_name, group,
                 article=None, revision=None, asvar=None):
        self.url_name = 'wiki_' + url_name
        self.group = group
        self.article = article
        self.revision = revision
        self.asvar = asvar

    def resolve(self, attrname, context):
        attr = getattr(self, attrname)
        if attr is None:
            return
        return attr.resolve(context)

    def render(self, context):
        group = self.resolve('group', context)
        article = self.resolve('article', context)
        revision = self.resolve('revision', context)

        kw = {}

        url = ''

        if article is not None:
            kw['title'] = article.title

        if revision is not None:
            kw['revision'] = revision

        # when the variable is not found is the context,
        # the var is resolved as ''.
        if group != '':
            app = group._meta.app_label
            urlconf = '.'.join([app, 'urls'])
            kw['group_slug'] = group.slug


            try:
                url_bits = ['/', app, reverse(self.url_name, urlconf, kwargs=kw)]
                url = ''.join(url_bits) # @@@ hardcoding /app_name/wiki_url/
            except NoReverseMatch, err:
                if self.asvar is None:
                    raise
        else:
            url = reverse(self.url_name, kwargs=kw)

        if self.asvar is not None:
            context[self.asvar] = url
            return ''
        else:
            return url

def wikiurl(parser, token):
    """
    Returns an absolute URL matching given url name with its parameters,
    given the articles group and (optional) article and revision number.

    This is a way to define links that aren't tied to our URL configuration::

        {% wikiurl edit group article %}

    The first argument is a url name, without the ``wiki_`` prefix.

    For example if you have a view ``app_name.client`` taking client's id and
    the corresponding line in a URLconf looks like this::

        url('^edit/(\w+)/$', 'wiki.edit_article', name='wiki_edit')

    and this app's URLconf is included into the project's URLconf under some
    path::

        url('^groups/(?P<group_slug>\w+)/mywiki/', include('wiki.urls'), kwargs)

    then in a template you can create a link to edit a certain article like this::

        {% wikiurl edit group article %}

    The URL will look like ``groups/some_group/mywiki/edit/WikiWord/``.

    This tag is also able to set a context variable instead of returning the
    found URL by specifying it with the 'as' keyword::

        {% wikiurl edit group article as wiki_article_url %}

    """
    bits = token.contents.split(' ')
    kwargs = {}
    if len(bits) == 3: # {% wikiurl url_name group %}
        url_name = bits[1]
        group = parser.compile_filter(bits[2])
    elif len(bits) == 4: # {% wikiurl url_name group article %}
        url_name = bits[1]
        group = parser.compile_filter(bits[2])
        kwargs['article'] = parser.compile_filter(bits[3])
    elif len(bits) == 5: # {% wikiurl url_name group as var %} or {% wikiurl url_name group article revision %}
        url_name = bits[1]
        group = parser.compile_filter(bits[2])
        if bits[3] == "as":
            kwargs['asvar'] = bits[4]
        else:
            kwargs['article'] = parser.compile_filter(bits[3])
            kwargs['revision'] = parser.compile_filter(bits[4])
    elif len(bits) == 6: # {% wikiurl url_name group article as var %}
        if bits[4] == "as":
            raise TemplateSyntaxError("4th argument to %s should be 'as'" % bits[0])
        url_name = bits[1]
        group = parser.compile_filter(bits[2])
        kwargs['article'] = parser.compile_filter(bits[3])
        kwargs['asvar'] = parser.compile_filter(bits[5])
    elif len(bits) == 7: # {% wikiurl url_name group article revision as var %}
        url_name = bits[1]
        group = parser.compile_filter(bits[2])
        kwargs['article'] = parser.compile_filter(bits[3])
        kwargs['revision'] = parser.compile_filter(bits[4])
        kwargs['asvar'] = parser.compile_filter(bits[6])
    else:
        raise TemplateSyntaxError("wrong number of arguments to %s" % bits[0])
    return WikiURLNode(url_name, group, **kwargs)

wikiurl = register.tag(wikiurl)
