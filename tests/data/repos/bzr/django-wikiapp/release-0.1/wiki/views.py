# -*- coding: utf-8 -*-

from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.http import (Http404, HttpResponseRedirect,
                         HttpResponseNotAllowed, HttpResponse, HttpResponseForbidden)
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic.simple import redirect_to
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.syndication.feeds import FeedDoesNotExist

from wiki.forms import ArticleForm, SearchForm
from wiki.models import Article, ChangeSet
from wiki.feeds import (RssArticleHistoryFeed, AtomArticleHistoryFeed,
                        RssHistoryFeed, AtomHistoryFeed)
from wiki.utils import get_ct, login_required


# Settings

#  lock duration in minutes
try:
    WIKI_LOCK_DURATION = settings.WIKI_LOCK_DURATION
except AttributeError:
    WIKI_LOCK_DURATION = 15

try:
    from notification import models as notification
except ImportError:
    notification = None

# default querysets
ALL_ARTICLES = Article.objects.all()
ALL_CHANGES = ChangeSet.objects.all()


def get_real_ip(request):
    """ Returns the real user IP, even if behind a proxy.
    Set BEHIND_PROXY to True in your settings if Django is
    running behind a proxy.
    """
    if getattr(settings, 'BEHIND_PROXY', False):
        return request.META['HTTP_X_FORWARDED_FOR']
    return request.META['REMOTE_ADDR']

def get_articles_by_group(article_qs, group_slug=None,
                          group_slug_field=None, group_qs=None):
    group = None
    if group_slug is not None:
        group = get_object_or_404(group_qs,
                                  **{group_slug_field: group_slug})
        article_qs = article_qs.filter(content_type=get_ct(group),
                                       object_id=group.id)
    return article_qs, group

def get_articles_for_object(object, article_qs=None):
    if article_qs is None:
        article_qs = ALL_ARTICLES
    return article_qs.filter( content_type=get_ct(object),
                                       object_id=object.id)

def get_url(urlname, group=None, args=None, kw=None):
    if group is None:
        return reverse(urlname, args=args)
    else:
        app = group._meta.app_label
        urlconf = '.'.join([app, 'urls'])
        url = reverse(urlname, urlconf, kwargs=kw)
        return ''.join(['/', app, url]) # @@@ harcoded: /app/.../


class ArticleEditLock(object):
    """ A soft lock to edting an article.
    """

    def __init__(self, title, request, message_template=None):
        self.title = title
        self.user_ip = get_real_ip(request)
        self.created_at = datetime.now()

        if message_template is None:
            message_template = ('Possible edit conflict:'
            ' another user started editing this article at %s')

        self.message_template = message_template

        cache.set(title, self, WIKI_LOCK_DURATION*60)

    def create_message(self, request):
        """ Send a message to the user if there is another user
        editing this article.
        """
        if not self.is_mine(request):
            user = request.user
            user.message_set.create(
                message=self.message_template%self.created_at)

    def is_mine(self, request):
        return self.user_ip == get_real_ip(request)


def has_read_perm(user, group, is_member, is_private):
    """ Return True if the user has permission to *read*
    Articles, False otherwise.
    """
    if (group is None) or (is_member is None) or is_member(user, group):
        return True
    if (is_private is not None) and is_private(group):
        return False
    return True

def has_write_perm(user, group, is_member):
    """ Return True if the user have permission to edit Articles,
    False otherwise.
    """
    if (group is None) or (is_member is None) or is_member(user, group):
        return True
    return False


@login_required
def article_list(request,
                 group_slug=None, group_slug_field=None, group_qs=None,
                 article_qs=ALL_ARTICLES,
                 ArticleClass=Article,
                 SearchFormClass=SearchForm,
                 template_name='index.html',
                 template_dir='wiki',
                 extra_context=None,
                 is_member=None,
                 is_private=None,
                 *args, **kw):
    if request.method == 'GET':

        articles, group = get_articles_by_group(
            article_qs, group_slug,
            group_slug_field, group_qs)

        allow_read = has_read_perm(request.user, group, is_member, is_private)
        allow_write = has_write_perm(request.user, group, is_member)

        if not allow_read:
            return HttpResponseForbidden()

        articles = articles.order_by('-created_at')

        search_form = SearchFormClass()

        template_params = {'articles': articles,
                           'search_form': search_form,
                           'allow_write': allow_write}

        if group_slug is not None:
            template_params['group'] = group
            new_article = ArticleClass(title="NewArticle",
                                       content_type=get_ct(group),
                                       object_id=group.id)
        else:
            new_article = ArticleClass(title="NewArticle")
        template_params['new_article'] = new_article
        if extra_context is not None:
            template_params.update(extra_context)

        return render_to_response('/'.join([template_dir, template_name]),
                                  template_params,
                                  context_instance=RequestContext(request))
    return HttpResponseNotAllowed(['GET'])


@login_required
def view_article(request, title,
                 ArticleClass=Article, # to create an unsaved instance
                 group_slug=None, group_slug_field=None, group_qs=None,
                 article_qs=ALL_ARTICLES,
                 template_name='view.html',
                 template_dir='wiki',
                 extra_context=None,
                 is_member=None,
                 is_private=None,
                 *args, **kw):

    if request.method == 'GET':
        article_args = {'title': title}
        if group_slug is not None:
            group = get_object_or_404(group_qs,**{group_slug_field: group_slug})
            article_args.update({'content_type': get_ct(group),
                                 'object_id': group.id})
            allow_read = has_read_perm(request.user, group, is_member,
                                       is_private)
            allow_write = has_write_perm(request.user, group, is_member)
        else:
            allow_read = allow_write = True

        if not allow_read:
            return HttpResponseForbidden()

        try:
            article = article_qs.get(**article_args)
            if notification is not None:
                is_observing = notification.is_observing(article, request.user)
            else:
                is_observing = False
        except ArticleClass.DoesNotExist:
            article = ArticleClass(**article_args)
            is_observing = False

        template_params = {'article': article,
                           'allow_write': allow_write}

        if notification is not None:
            template_params.update({'is_observing': is_observing,
                                    'can_observe': True})

        if group_slug is not None:
            template_params['group'] = group
        if extra_context is not None:
            template_params.update(extra_context)

        return render_to_response('/'.join([template_dir, template_name]),
                                  template_params,
                                  context_instance=RequestContext(request))
    return HttpResponseNotAllowed(['GET'])


@login_required
def edit_article(request, title,
                 group_slug=None, group_slug_field=None, group_qs=None,
                 article_qs=ALL_ARTICLES,
                 ArticleClass=Article, # to get the DoesNotExist exception
                 ArticleFormClass=ArticleForm,
                 template_name='edit.html',
                 template_dir='wiki',
                 extra_context=None,
                 check_membership=False,
                 is_member=None,
                 is_private=None,
                 *args, **kw):

    group = None
    article_args = {'title': title}
    if group_slug is not None:
        group = get_object_or_404(group_qs,**{group_slug_field: group_slug})
        group_ct = get_ct(group)
        article_args.update({'content_type': group_ct,
                             'object_id': group.id})
        allow_read = has_read_perm(request.user, group, is_member,
                                   is_private)
        allow_write = has_write_perm(request.user, group, is_member)
    else:
        allow_read = allow_write = True

    if not allow_write:
        return HttpResponseForbidden()

    try:
        article = article_qs.get(**article_args)
    except ArticleClass.DoesNotExist:
        article = None

    if request.method == 'POST':

        form = ArticleFormClass(request.POST, instance=article)

        if form.is_valid():

            if request.user.is_authenticated():
                form.editor = request.user
                if article is None:
                    user_message = u"Your article was created successfully."
                else:
                    user_message = u"Your article was edited successfully."
                request.user.message_set.create(message=user_message)

            if ((article is None) and (group_slug is not None)):
                form.group = group

            new_article, changeset = form.save()

            url = get_url('wiki_article', group,
                          [new_article.title],
                          {'title': new_article.title,
                           'group_slug': group_slug})

            return redirect_to(request, url)

    elif request.method == 'GET':
        user_ip = get_real_ip(request)

        lock = cache.get(title, None)
        if lock is None:
            lock = ArticleEditLock(title, request)
        lock.create_message(request)

        initial = {'user_ip': user_ip}
        if group_slug is not None:
            initial.update({'content_type': group_ct.id,
                            'object_id': group.id})

        if article is None:
            initial.update({'title': title,
                            'action': 'create'})
            form = ArticleFormClass(initial=initial)
        else:
            initial['action'] = 'edit'
            form = ArticleFormClass(instance=article,
                                    initial=initial)

    template_params = {'form': form}

    if group_slug is not None:
        template_params['group'] = group
    if extra_context is not None:
        template_params.update(extra_context)

    return render_to_response('/'.join([template_dir, template_name]),
                              template_params,
                              context_instance=RequestContext(request))


@login_required
def view_changeset(request, title, revision,
                   group_slug=None, group_slug_field=None, group_qs=None,
                   article_qs=ALL_ARTICLES,
                   changes_qs=ALL_CHANGES,
                   template_name='changeset.html',
                   template_dir='wiki',
                   extra_context=None,
                   is_member=None,
                   is_private=None,
                   *args, **kw):

    if request.method == "GET":
        article_args = {'article__title': title}
        if group_slug is not None:
            group = get_object_or_404(group_qs,**{group_slug_field: group_slug})
            article_args.update({'article__content_type': get_ct(group),
                                 'article__object_id': group.id})
        changeset = get_object_or_404(
            changes_qs,
            revision=int(revision),
            **article_args)

        article_args = {'title': title}
        if group_slug is not None:
            group = get_object_or_404(group_qs,**{group_slug_field: group_slug})
            article_args.update({'content_type': get_ct(group),
                                 'object_id': group.id})
            allow_read = has_read_perm(request.user, group, is_member,
                                       is_private)
            allow_write = has_write_perm(request.user, group, is_member)
        else:
            allow_read = allow_write = True

        if not allow_read:
            return HttpResponseForbidden()

        article = article_qs.get(**article_args)

        template_params = {'article': article,
                           'article_title': article.title,
                           'changeset': changeset,
                           'allow_write': allow_write}

        if group_slug is not None:
            template_params['group'] = group
        if extra_context is not None:
            template_params.update(extra_context)

        return render_to_response('/'.join([template_dir, template_name]),
                                  template_params,
                                  context_instance=RequestContext(request))
    return HttpResponseNotAllowed(['GET'])


@login_required
def article_history(request, title,
                    group_slug=None, group_slug_field=None, group_qs=None,
                    article_qs=ALL_ARTICLES,
                    template_name='history.html',
                    template_dir='wiki',
                    extra_context=None,
                    is_member=None,
                    is_private=None,
                    *args, **kw):

    if request.method == 'GET':

        article_args = {'title': title}
        if group_slug is not None:
            group = get_object_or_404(group_qs,**{group_slug_field: group_slug})
            article_args.update({'content_type': get_ct(group),
                                 'object_id': group.id})
            allow_read = has_read_perm(request.user, group, is_member,
                                       is_private)
            allow_write = has_write_perm(request.user, group, is_member)
        else:
            allow_read = allow_write = True

        if not allow_read:
            return HttpResponseForbidden()

        article = get_object_or_404(article_qs, **article_args)
        changes = article.changeset_set.filter(
            reverted=False).order_by('-revision')

        template_params = {'article': article,
                           'changes': changes,
                           'allow_write': allow_write}
        if group_slug is not None:
            template_params['group'] = group
        if extra_context is not None:
            template_params.update(extra_context)

        return render_to_response('/'.join([template_dir, template_name]),
                                  template_params,
                                  context_instance=RequestContext(request))

    return HttpResponseNotAllowed(['GET'])


@login_required
def revert_to_revision(request, title,
                       group_slug=None, group_slug_field=None, group_qs=None,
                       article_qs=ALL_ARTICLES,
                       extra_context=None,
                       is_member=None,
                       is_private=None,
                       *args, **kw):

    if request.method == 'POST':

        revision = int(request.POST['revision'])

        article_args = {'title': title}

        group = None
        if group_slug is not None:
            group = get_object_or_404(group_qs,**{group_slug_field: group_slug})
            article_args.update({'content_type': get_ct(group),
                                 'object_id': group.id})
            allow_read = has_read_perm(request.user, group, is_member,
                                       is_private)
            allow_write = has_write_perm(request.user, group, is_member)
        else:
            allow_read = allow_write = True

        if not (allow_read or allow_write):
            return HttpResponseForbidden()

        article = get_object_or_404(article_qs, **article_args)

        if request.user.is_authenticated():
            article.revert_to(revision, get_real_ip(request), request.user)
        else:
            article.revert_to(revision, get_real_ip(request))


        if request.user.is_authenticated():
            request.user.message_set.create(
                message=u"The article was reverted successfully.")

        url = get_url('wiki_article_history', group,
                      [title], {'title': title,
                                'group_slug': group_slug})

        return redirect_to(request, url)

    return HttpResponseNotAllowed(['POST'])


@login_required
def search_article(request,
                   group_slug=None, group_slug_field=None, group_qs=None,
                   article_qs=ALL_ARTICLES,
                   SearchFormClass=SearchForm,
                   extra_context=None,
                   is_member=None,
                   is_private=None,
                   *args, **kw):
    if request.method == 'POST':
        search_form = SearchFormClass(request.POST)
        if search_form.is_valid():
            search_term = search_form.cleaned_data['search_term']

            group = None
            if group_slug is not None:
                group = get_object_or_404(group_qs,
                                          **{group_slug_field: group_slug})
                allow_read = has_read_perm(request.user, group, is_member,
                                           is_private)
            else:
                allow_read = True

            if not allow_read:
                return Http404()

            # go to article by title
            url = get_url('wiki_article', group,
                          [search_term], {'title': search_term,
                                          'group_slug': group_slug})

            return redirect_to(request, url)

    return HttpResponseNotAllowed(['POST'])


@login_required
def history(request,
            group_slug=None, group_slug_field=None, group_qs=None,
            article_qs=ALL_ARTICLES, changes_qs=ALL_CHANGES,
            template_name='recentchanges.html',
            template_dir='wiki',
            extra_context=None,
            *args, **kw):

    if request.method == 'GET':
        if  group_slug is not None:
            group = get_object_or_404(group_qs,
                                      **{group_slug_field : group_slug})
            changes_qs = changes_qs.filter(article__content_type=get_ct(group),
                                           article__object_id=group.id)
            allow_read = has_read_perm(request.user, group, is_member,
                                       is_private)
            allow_write = has_write_perm(request.user, group, is_member)
        else:
            allow_read = allow_write = True

        if not allow_read:
            return HttpResponseForbidden()

        template_params = {'changes': changes_qs.order_by('-modified'),
                           'allow_write': allow_write}
        if group_slug is not None:
            template_params['group'] = group_slug

        if extra_context is not None:
            template_params.update(extra_context)

        return render_to_response('/'.join([template_dir, template_name]),
                                  template_params,
                                  context_instance=RequestContext(request))
    return HttpResponseNotAllowed(['GET'])


@login_required
def observe_article(request, title,
                    group_slug=None, group_slug_field=None, group_qs=None,
                    article_qs=ALL_ARTICLES,
                    template_name='recentchanges.html',
                    template_dir='wiki',
                    extra_context=None,
                    is_member=None,
                    is_private=None,
                    *args, **kw):
    if request.method == 'POST':

        article_args = {'title': title}
        group = None
        if group_slug is not None:
            group = get_object_or_404(group_qs,**{group_slug_field: group_slug})
            article_args.update({'content_type': get_ct(group),
                                 'object_id': group.id})
            allow_read = has_read_perm(request.user, group, is_member,
                                       is_private)
        else:
            allow_read = True

        if not allow_read:
            return HttpResponseForbidden()

        article = get_object_or_404(article_qs, **article_args)

        notification.observe(article, request.user,
                             'wiki_observed_article_changed')

        url = get_url('wiki_article', group,
                      [article.title], {'title': article.title,
                                        'group_slug': group_slug})

        return redirect_to(request, url)

    return HttpResponseNotAllowed(['POST'])


@login_required
def stop_observing_article(request, title,
                           group_slug=None, group_slug_field=None, group_qs=None,
                           article_qs=ALL_ARTICLES,
                           template_name='recentchanges.html',
                           template_dir='wiki',
                           extra_context=None,
                           is_member=None,
                           is_private=None,
                           *args, **kw):
    if request.method == 'POST':

        article_args = {'title': title}
        group = None
        if group_slug is not None:
            group = get_object_or_404(group_qs,**{group_slug_field: group_slug})
            article_args.update({'content_type': get_ct(group),
                                 'object_id': group.id})
            allow_read = has_read_perm(request.user, group, is_member,
                                       is_private)
        else:
            allow_read = True

        if not allow_read:
            return HttpResponseForbidden()

        article = get_object_or_404(article_qs, **article_args)

        notification.stop_observing(article, request.user)

        url = get_url('wiki_article', group,
                      [article.title], {'title': article.title,
                                        'group_slug': group_slug})

        return redirect_to(request, url)
    return HttpResponseNotAllowed(['POST'])


def article_history_feed(request, feedtype, title,
                         group_slug=None, group_slug_field=None, group_qs=None,
                         article_qs=ALL_ARTICLES, changes_qs=ALL_CHANGES,
                         extra_context=None,
                         is_member=None,
                         is_private=None,
                         *args, **kw):

    feeds = {'rss' : RssArticleHistoryFeed,
             'atom' : AtomArticleHistoryFeed}
    ArticleHistoryFeed = feeds.get(feedtype, RssArticleHistoryFeed)

    try:
        feedgen = ArticleHistoryFeed(title, request,
                                     group_slug, group_slug_field, group_qs,
                                     article_qs, changes_qs,
                                     extra_context,
                                     *args, **kw).get_feed(title)
    except FeedDoesNotExist:
        raise Http404

    response = HttpResponse(mimetype=feedgen.mime_type)
    feedgen.write(response, 'utf-8')
    return response


def history_feed(request, feedtype,
                 group_slug=None, group_slug_field=None, group_qs=None,
                 article_qs=ALL_ARTICLES, changes_qs=ALL_CHANGES,
                 extra_context=None,
                 is_member=None,
                 is_private=None,
                 *args, **kw):

    feeds = {'rss' : RssHistoryFeed,
             'atom' : AtomHistoryFeed}
    HistoryFeed = feeds.get(feedtype, RssHistoryFeed)

    try:
        feedgen = HistoryFeed(request,
                              group_slug, group_slug_field, group_qs,
                              article_qs, changes_qs,
                              extra_context,
                              *args, **kw).get_feed()
    except FeedDoesNotExist:
        raise Http404

    response = HttpResponse(mimetype=feedgen.mime_type)
    feedgen.write(response, 'utf-8')
    return response

