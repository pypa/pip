from django.contrib.syndication.feeds import Feed, FeedDoesNotExist
from django.utils.feedgenerator import Atom1Feed
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404, render_to_response
from django.template import Context, Template
from django.template.loader import get_template
from wiki.models import ChangeSet, Article
from wiki.utils import get_ct
import atomformat as atom

ALL_ARTICLES = Article.objects.all()
ALL_CHANGES = ChangeSet.objects.all()

class RssHistoryFeed(Feed):

    title = 'History for all articles'
    link = '/wiki/'
    description = 'Recent changes in wiki'

    def __init__(self, request,
                 group_slug=None, group_slug_field=None, group_qs=None, 
                 article_qs=ALL_ARTICLES, changes_qs=ALL_CHANGES, 
                 extra_context=None, 
                 title_template = u'feeds/history_title.html', 
                 description_template = u'feeds/history_description.html', 
                 *args, **kw):

        if  group_slug is not None:
            group = get_object_or_404(group_qs, 
                                      **{group_slug_field : group_slug})
            self.changes_qs = changes_qs.filter(article__content_type=get_ct(group), 
                                                article__object_id=group.id)
        else:
            self.changes_qs = changes_qs

        self.title_template = title_template
        self.description_template = description_template
        super(RssHistoryFeed, self).__init__('', request)

    def items(self):
        return self.changes_qs.order_by('-modified')[:30]
        
    def item_pubdate(self, item):
        """
        Return the item's pubdate. It's this modified date
        """
        return item.modified


class AtomHistoryFeed(atom.Feed):

    feed_title = 'History for all articles'
    feed_subtitle = 'Recent changes in wiki'

    def __init__(self, request,
                 group_slug=None, group_slug_field=None, group_qs=None, 
                 article_qs=ALL_ARTICLES, changes_qs=ALL_CHANGES, 
                 extra_context=None, 
                 title_template = u'feeds/history_title.html', 
                 description_template = u'feeds/history_description.html', 
                 *args, **kw):

        if  group_slug is not None:
            group = get_object_or_404(group_qs, 
                                      **{group_slug_field : group_slug})
            self.changes_qs = changes_qs.filter(article__content_type=get_ct(group), 
                                                article__object_id=group.id)
        else:
            self.changes_qs = changes_qs

        self.title_template = get_template(title_template)
        self.description_template = get_template(description_template)
        super(AtomHistoryFeed, self).__init__('', request)

    def feed_id(self):
        return "feed_id"

    def items(self):
        return self.changes_qs.order_by('-modified')[:30]

    def item_id(self, item):
        return "%s" % item.id

    def item_title(self, item):
        c = Context({'obj' : item})
        return self.title_template.render(c)

    def item_updated(self, item):
        return item.modified

    def item_authors(self, item):
        if item.is_anonymous_change():
            return [{'name' : _('Anonimous')},]
        return [{'name' : item.editor.username},]

    def item_links(self, item):
        return [{'href': item.get_absolute_url()}, ]

    def item_content(self, item):
        c = Context({'obj' : item,})
        return ({'type': 'html'}, self.description_template.render(c))


class RssArticleHistoryFeed(Feed):

    def __init__(self, title, request, 
                group_slug=None, group_slug_field=None, group_qs=None,
                article_qs=ALL_ARTICLES, changes_qs=ALL_CHANGES,
                extra_context=None,
                title_template = u'feeds/history_title.html',
                description_template = u'feeds/history_description.html',
                *args, **kw):

        if  group_slug is not None:
            group = get_object_or_404(group_qs,
                                      **{group_slug_field : group_slug})
            self.article_qs = article_qs.filter(content_type=get_ct(group),
                                           object_id=group.id)
        else:
            self.article_qs = article_qs

        self.title_template = title_template
        self.description_template = description_template
        super(RssArticleHistoryFeed, self).__init__(title, request)

    def get_object(self, bits):
        return self.article_qs.get(title = bits[0])

    def title(self, obj):
        return "History for: %s " % obj.title

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return obj.get_absolute_url()

    def description(self, obj):
        return "Recent changes in %s" % obj.title

    def items(self, obj):
        return ChangeSet.objects.filter(article__id__exact=obj.id).order_by('-modified')[:30]

    def item_pubdate(self, item):
        """
        Returns the modified date
        """
        return item.modified


class AtomArticleHistoryFeed(atom.Feed):
    
    def __init__(self, title, request, 
                group_slug=None, group_slug_field=None, group_qs=None,
                article_qs=ALL_ARTICLES, changes_qs=ALL_CHANGES,
                extra_context=None,
                title_template = u'feeds/history_title.html',
                description_template = u'feeds/history_description.html',
                *args, **kw):

        if  group_slug is not None:
            group = get_object_or_404(group_qs,
                                      **{group_slug_field : group_slug})
            self.article_qs = article_qs.filter(content_type=get_ct(group),
                                           object_id=group.id)
        else:
            self.article_qs = article_qs

        self.title_template = get_template(title_template)
        self.description_template = get_template(description_template)
        super(AtomArticleHistoryFeed, self).__init__('', request)

    def get_object(self, bits):
        return self.article_qs.get(title = bits[0])

    def feed_title(self, obj):
        return "History for: %s " % obj.title

    def feed_subtitle(self, obj):
        return "Recent changes in %s" % obj.title

    def feed_id(self):
        return "feed_id"

    def items(self, obj):
        return ChangeSet.objects.filter(article__id__exact=obj.id).order_by('-modified')[:30]

    def item_id(self, item):
        return "%s" % item.id

    def item_title(self, item):
        c = Context({'obj' : item})
        return self.title_template.render(c)

    def item_updated(self, item):
        return item.modified

    def item_authors(self, item):
        if item.is_anonymous_change():
            return [{'name' : _('Anonimous')},]
        return [{'name' : item.editor.username},]

    def item_links(self, item):
        return [{'href': item.get_absolute_url()},]

    def item_content(self, item):
        c = Context({'obj' : item, })
        return ({'type': 'html'}, self.description_template.render(c))
