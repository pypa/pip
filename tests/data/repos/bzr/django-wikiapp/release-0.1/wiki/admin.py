# -*- coding: utf-8 -*-

from django.contrib import admin

from wiki.models import Article, ChangeSet


class InlineChangeSet(admin.TabularInline):
    model = ChangeSet
    extra = 0
    raw_id_fields = ('editor',)

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'markup', 'created_at')
    list_filter = ('title',)
    ordering = ('last_update',)
    fieldsets = (
        (None, {'fields': ('title', 'content', 'markup')}),
        ('Creator', {'fields': ('creator', 'creator_ip'),
                     'classes': ('collapse', 'wide')}),
        ('Group', {'fields': ('object_id', 'content_type'),
                     'classes': ('collapse', 'wide')}),
    )
    raw_id_fields = ('creator',)
    inlines = [InlineChangeSet]

admin.site.register(Article, ArticleAdmin)


class ChangeSetAdmin(admin.ModelAdmin):
    list_display = ('article', 'revision', 'old_title', 'old_markup',
                    'editor', 'editor_ip', 'reverted', 'modified',
                    'comment')
    list_filter = ('old_title', 'content_diff')
    ordering = ('modified',)
    fieldsets = (
        ('Article', {'fields': ('article',)}),
        ('Differences', {'fields': ('old_title', 'old_markup',
                                    'content_diff')}),
        ('Other', {'fields': ('comment', 'modified', 'revision', 'reverted'),
                   'classes': ('collapse', 'wide')}),
        ('Editor', {'fields': ('editor', 'editor_ip'),
                    'classes': ('collapse', 'wide')}),
    )
    raw_id_fields = ('editor',)

admin.site.register(ChangeSet, ChangeSetAdmin)
