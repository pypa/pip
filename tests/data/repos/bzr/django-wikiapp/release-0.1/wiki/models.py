from datetime import datetime
from django.core.urlresolvers import reverse

# Google Diff Match Patch library
# http://code.google.com/p/google-diff-match-patch
from diff_match_patch import diff_match_patch

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from tagging.fields import TagField
from tagging.models import Tag

try:
    from notification import models as notification
    from django.db.models import signals
except ImportError:
    notification = None

# We dont need to create a new one everytime
dmp = diff_match_patch()

def diff(txt1, txt2):
    """Create a 'diff' from txt1 to txt2."""
    patch = dmp.patch_make(txt1, txt2)
    return dmp.patch_toText(patch)

try:
    markup_choices = settings.WIKI_MARKUP_CHOICES
except AttributeError:
    markup_choices = (
        ('crl', _(u'Creole')),
        ('rst', _(u'reStructuredText')),
        ('txl', _(u'Textile')),
        ('mrk', _(u'Markdown')),
    )


class Article(models.Model):
    """ A wiki page.
    """
    title = models.CharField(_(u"Title"), max_length=50)
    content = models.TextField(_(u"Content"))
    summary = models.CharField(_(u"Summary"), max_length=150,
                               null=True, blank=True)
    markup = models.CharField(_(u"Content Markup"), max_length=3,
                              choices=markup_choices,
                              null=True, blank=True)
    creator = models.ForeignKey(User, verbose_name=_('Article Creator'),
                                null=True)
    creator_ip = models.IPAddressField(_("IP Address of the Article Creator"),
                                       blank=True, null=True)
    created_at = models.DateTimeField(default=datetime.now)
    last_update = models.DateTimeField(blank=True, null=True)

    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    group = generic.GenericForeignKey('content_type', 'object_id')

    tags = TagField()

    class Meta:
        verbose_name = _(u'Article')
        verbose_name_plural = _(u'Articles')

    def get_absolute_url(self):
        if self.group is None:
            return reverse('wiki_article', args=(self.title,))
        return self.group.get_absolute_url() + 'wiki/' + self.title

    def save(self, force_insert=False, force_update=False):
        self.last_update = datetime.now()
        super(Article, self).save(force_insert, force_update)

    def latest_changeset(self):
        try:
            return self.changeset_set.filter(
                reverted=False).order_by('-revision')[0]
        except IndexError:
            return ChangeSet.objects.none()

    def new_revision(self, old_content, old_title, old_markup,
                     comment, editor_ip, editor):
        '''Create a new ChangeSet with the old content.'''

        content_diff = diff(self.content, old_content)

        cs = ChangeSet.objects.create(
            article=self,
            comment=comment,
            editor_ip=editor_ip,
            editor=editor,
            old_title=old_title,
            old_markup=old_markup,
            content_diff=content_diff)

        if None not in (notification, self.creator):
            if editor is None:
                editor = editor_ip
            notification.send([self.creator], "wiki_article_edited",
                              {'article': self, 'user': editor})

        return cs

    def revert_to(self, revision, editor_ip, editor=None):
        """ Revert the article to a previuos state, by revision number.
        """
        changeset = self.changeset_set.get(revision=revision)
        changeset.reapply(editor_ip, editor)


    def __unicode__(self):
        return self.title



class ChangeSetManager(models.Manager):

    def all_later(self, revision):
        """ Return all changes later to the given revision.
        Util when we want to revert to the given revision.
        """
        return self.filter(revision__gt=int(revision))


class NonRevertedChangeSetManager(ChangeSetManager):

    def get_default_queryset(self):
        super(PublishedBookManager, self).get_query_set().filter(
            reverted=False)


class ChangeSet(models.Model):
    """A report of an older version of some Article."""

    article = models.ForeignKey(Article, verbose_name=_(u"Article"))

    # Editor identification -- logged or anonymous
    editor = models.ForeignKey(User, verbose_name=_(u'Editor'),
                               null=True)
    editor_ip = models.IPAddressField(_(u"IP Address of the Editor"))

    # Revision number, starting from 1
    revision = models.IntegerField(_(u"Revision Number"))

    # How to recreate this version
    old_title = models.CharField(_(u"Old Title"), max_length=50, blank=True)
    old_markup = models.CharField(_(u"Article Content Markup"), max_length=3,
                                  choices=markup_choices,
                                  null=True, blank=True)
    content_diff = models.TextField(_(u"Content Patch"), blank=True)

    comment = models.CharField(_(u"Editor comment"), max_length=50, blank=True)
    modified = models.DateTimeField(_(u"Modified at"), default=datetime.now)
    reverted = models.BooleanField(_(u"Reverted Revision"), default=False)

    objects = ChangeSetManager()
    non_reverted_objects = NonRevertedChangeSetManager()

    class Meta:
        verbose_name = _(u'Change set')
        verbose_name_plural = _(u'Change sets')
        get_latest_by  = 'modified'
        ordering = ('-revision',)

    def __unicode__(self):
        return u'#%s' % self.revision

    @models.permalink
    def get_absolute_url(self):
        if self.article.group is None:
            return ('wiki_changeset', (),
                    {'title': self.article.title,
                     'revision': self.revision})
        return ('wiki_changeset', (),
                {'group_slug': self.article.group.slug,
                 'title': self.article.title,
                 'revision': self.revision})


    def is_anonymous_change(self):
        return self.editor is None

    def reapply(self, editor_ip, editor):
        """ Return the Article to this revision.
        """

        # XXX Would be better to exclude reverted revisions
        #     and revisions previous/next to reverted ones
        next_changes = self.article.changeset_set.filter(
            revision__gt=self.revision).order_by('-revision')

        article = self.article

        content = None
        for changeset in next_changes:
            if content is None:
                content = article.content
            patch = dmp.patch_fromText(changeset.content_diff)
            content = dmp.patch_apply(patch, content)[0]

            changeset.reverted = True
            changeset.save()

        old_content = article.content
        old_title = article.title
        old_markup = article.markup

        article.content = content
        article.title = changeset.old_title
        article.markup = changeset.old_markup
        article.save()

        article.new_revision(
            old_content=old_content, old_title=old_title,
            old_markup=old_markup,
            comment="Reverted to revision #%s" % self.revision,
            editor_ip=editor_ip, editor=editor)

        self.save()

        if None not in (notification, self.editor):
            notification.send([self.editor], "wiki_revision_reverted",
                              {'revision': self, 'article': self.article})

    def save(self, force_insert=False, force_update=False):
        """ Saves the article with a new revision.
        """
        if self.id is None:
            try:
                self.revision = ChangeSet.objects.filter(
                    article=self.article).latest().revision + 1
            except self.DoesNotExist:
                self.revision = 1
        super(ChangeSet, self).save(force_insert, force_update)

    def display_diff(self):
        ''' Returns a HTML representation of the diff.
        '''

        # well, it *will* be the old content
        old_content = self.article.content

        # newer non-reverted revisions of this article, starting from this
        newer_changesets = ChangeSet.non_reverted_objects.filter(
            article=self.article,
            revision__gte=self.revision)

        # apply all patches to get the content of this revision
        for i, changeset in enumerate(newer_changesets):
            patches = dmp.patch_fromText(changeset.content_diff)
            if len(newer_changesets) == i+1:
                # we need to compare with the next revision after the change
                next_rev_content = old_content
            old_content = dmp.patch_apply(patches, old_content)[0]

        diffs = dmp.diff_main(old_content, next_rev_content)
        return dmp.diff_prettyHtml(diffs)

if notification is not None:
    signals.post_save.connect(notification.handle_observations, sender=Article)
