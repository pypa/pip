# -*- coding: utf-8 -*-
import re

from django import forms
from django.forms import widgets
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from wiki.models import Article
from wiki.templatetags.wiki import WIKI_WORD_RE

wikiword_pattern = re.compile('^' + WIKI_WORD_RE + '$')


class ArticleForm(forms.ModelForm):

    summary = forms.CharField(widget=forms.Textarea)

    comment = forms.CharField(required=False)
    user_ip = forms.CharField(widget=forms.HiddenInput)

    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.all(),
        required=False,
        widget=forms.HiddenInput)
    object_id = forms.IntegerField(required=False,
                                   widget=forms.HiddenInput)

    action = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = Article
        exclude = ('creator', 'creator_ip',
                   'group', 'created_at', 'last_update')

    def clean_title(self):
        """ Page title must be a WikiWord.
        """
        title = self.cleaned_data['title']
        if not wikiword_pattern.match(title):
            raise forms.ValidationError(_('Must be a WikiWord.'))

        return title

    def clean(self):
        super(ArticleForm, self).clean()
        kw = {}

        if self.cleaned_data['action'] == 'create':
            try:
                kw['title'] = self.cleaned_data['title']
                kw['content_type'] = self.cleaned_data['content_type']
                kw['object_id'] = self.cleaned_data['object_id']
            except KeyError:
                pass # some error in this fields
            else:
                if Article.objects.filter(**kw).count():
                    raise forms.ValidationError(
                        _("An article with this title already exists."))

        return self.cleaned_data

    def save(self):
        # 0 - Extra data
        editor_ip = self.cleaned_data['user_ip']
        comment = self.cleaned_data['comment']

        # 1 - Get the old stuff before saving
        if self.instance.id is None:
            old_title = old_content = old_markup = ''
            new = True
        else:
            old_title = self.instance.title
            old_content = self.instance.content
            old_markup = self.instance.markup
            new = False

        # 2 - Save the Article
        article = super(ArticleForm, self).save()

        # 3 - Set creator and group
        editor = getattr(self, 'editor', None)
        group = getattr(self, 'group', None)
        if new:
            article.creator_ip = editor_ip
            if editor is not None:
                article.creator = editor
                article.group = group
            article.save()

        # 4 - Create new revision
        changeset = article.new_revision(
            old_content, old_title, old_markup,
            comment, editor_ip, editor)

        return article, changeset



class SearchForm(forms.Form):
    search_term = forms.CharField(required=True)
