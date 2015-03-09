from django.conf.urls.defaults import *
from django.conf import settings


urlpatterns = patterns('',
   url(r'^site_media/(?P<path>.*)$',
       'django.views.static.serve',
       {'document_root': settings.STATIC_MEDIA_PATH},
       name='wiki_static_media'),
)
