"""rustdesk_server_api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import django
from django.contrib import admin
from django.urls import path

from api.views import index
from api import views_front
if django.__version__.split('.')[0]>='4':
    from django.urls import re_path as url
    from django.conf.urls import  include
else:
    from django.conf.urls import  url, include
from django.views import static ##新增
from django.conf import settings


import os

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    # SSL 인증을 위한 경로 추가
    url(r'^\.well-known/pki-validation/(?P<path>.*)$', static.serve, {
        'document_root': os.path.join(settings.BASE_DIR, '.well-known', 'pki-validation'),
    }),
    path('administrator/', admin.site.urls),
    url(r'^default$', views_front.default_page),  # 기본 다운로드 페이지
    url(r'^download$', views_front.download_default),  # 기본 실행파일 다운로드
    url(r'^$', index),
    url(r'^api/', include('api.urls')),
    url(r'^webui/', include('webui.urls')),
    url(r'^static/(?P<path>.*)$', static.serve, {'document_root': settings.STATIC_ROOT}, name='static'),
    url(r'^media/(?P<path>.*)$', static.serve, {'document_root': settings.MEDIA_ROOT}, name='media'),
    url(r'^canvaskit@0.33.0/(?P<path>.*)$', static.serve, {'document_root': 'static/web_client/canvaskit@0.33.0'},name='web_client'),
    url(r'^(?P<username>[\w.@+-]+)$', views_front.public_support),
]

from django.conf.urls import static as sc
if not settings.DEBUG:
    urlpatterns += sc.static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += sc.static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)