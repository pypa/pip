from django import template
from django.conf import settings

register = template.Library()

@register.filter
def flatpagehist_diff_previous(self):
    return self.diff_previous()

@register.filter
def restructuredparts(value, **overrides):
    """return the restructured text parts"""
    try:
        from docutils.core import publish_parts
    except ImportError:
        if settings.DEBUG:
            raise template.TemplateSyntaxError, "Error in {% restructuredtext %} filter: The Python docutils library isn't installed."
        return value
    else:
        docutils_settings = dict(getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {}))
        docutils_settings.update(overrides)
        if 'halt_level' not in docutils_settings:
            docutils_settings['halt_level'] = 6
        return publish_parts(source=value, writer_name="html4css1", settings_overrides=docutils_settings)

@register.filter
def restructuredtext(value, **overrides):
    """The django version of this markup filter has an issue when only one title or subtitle is supplied in that
    they are dropped from the markup. This is due to the use of 'fragment' instead of something like 'html_body'.
    We do not want to use 'html_body' either due to some header/footer stuff we want to prevent, but we want to
    keep the title and subtitle. So we include them if present."""
    parts = restructuredparts(value, **overrides)
    if not isinstance(parts, dict):
        return value
    return parts["html_body"]

@register.filter
def restructuredtext_has_errors(value, do_raise=False):
    ## RED_FLAG: need to catch the explicit exceptions and not a catch all...
    try:
        restructuredparts(value, halt_level=2, traceback=1)
        return False
    except:
        if do_raise:
            raise
    return True

class ReStructuredTextNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        return restructuredtext(self.nodelist.render(context))

@register.tag("restructuredtext")
def rest_tag(parser, token):
    """
    Render the ReStructuredText into html. Will pre-render template code first.

    Example:
    ::

        {% restructuredtext %}
            ===================================
            To: {{ send_to }}
            ===================================
            {% include "email_form.rst" %}
        {% endrestructuredtext %}

    """
    nodelist = parser.parse(('endrestructuredtext',))
    parser.delete_first_token()
    return ReStructuredTextNode(nodelist)

@register.inclusion_tag("restructuredtext/dynamic.html", takes_context=True)
def rstflatpage(context):
    """
    The core content of the restructuredtext flatpage with history, editing,
    etc. for use in your 'flatpages/default.html' or custom template.

    Example:
    ::

        <html><head><title>{{ flatpage.title }}</title></head>
              <body>{% load restructuredtext %}{% rstflatpage %}</body>
        </html>


    This will inject one of 6 different page contents:

    * Just the flatpage.content for normal flatpages (so templates can be
      used with normal flatpages).
    * A custom 404 page (with optional create/restore form).
    * View current (with optional edit/history/delete form).
    * View version (with optional history/current/revert form).
    * Edit form (with preview/save/cancel).
    * History listing.
    """
    return context

@register.inclusion_tag("restructuredtext/feeds.html", takes_context=True)
def rstflatpage_feeds(context):
    """
    Optionally inserts the history feeds
    """
    return context
