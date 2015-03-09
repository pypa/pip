from django.db.models import signals

from django.utils.translation import ugettext_noop as _

try:
    from notification import models as notification

    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type("wiki_article_edited",
                                        _("Article Edited"),
                                        _("your article has been edited"))
        notification.create_notice_type("wiki_revision_reverted",
                                        _("Article Revision Reverted"),
                                        _("your revision has been reverted"))
        notification.create_notice_type("wiki_observed_article_changed",
                                        _("Observed Article Changed"),
                                        _("an article you observe has changed"))


    signals.post_syncdb.connect(create_notice_types,
                                sender=notification)
except ImportError:
    print "Skipping creation of NoticeTypes as notification app not found"
