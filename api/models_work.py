# cython:language_level=3
from django.db import models
from django.contrib import admin
from django.utils.translation import gettext as _


class RustDeskToken(models.Model):
    ''' Token
    '''
    username = models.CharField(verbose_name=_('사용자명'), max_length=20)
    rid = models.CharField(verbose_name=_('MDesk ID'), max_length=16)
    uid = models.CharField(verbose_name=_('사용자 ID'), max_length=16)
    uuid = models.CharField(verbose_name=_('uuid'), max_length=60)
    access_token = models.CharField(verbose_name=_('access_token'), max_length=60, blank=True)
    create_time = models.DateTimeField(verbose_name=_('로그인 시간'), auto_now_add=True)
    # expire_time = models.DateTimeField(verbose_name='过期时间')

    class Meta:
        ordering = ('-username',)
        verbose_name = "Token"
        verbose_name_plural = _("Token 목록")


class RustDeskTokenAdmin(admin.ModelAdmin):
    list_display = ('username', 'uid')
    search_fields = ('username', 'uid')
    list_filter = ('create_time', )  # 过滤器


class RustDeskTag(models.Model):
    ''' Tags
    '''
    uid = models.CharField(verbose_name=_('소유 사용자 ID'), max_length=16)
    tag_name = models.CharField(verbose_name=_('태그 이름'), max_length=60)
    tag_color = models.CharField(verbose_name=_('태그 색상'), max_length=60, blank=True)

    class Meta:
        ordering = ('-uid',)
        verbose_name = "Tags"
        verbose_name_plural = _("Tags 목록")


class RustDeskTagAdmin(admin.ModelAdmin):
    list_display = ('tag_name', 'uid', 'tag_color')
    search_fields = ('tag_name', 'uid')
    list_filter = ('uid', )


class RustDeskPeer(models.Model):
    ''' Pees
    '''
    uid = models.CharField(verbose_name=_('사용자 ID'), max_length=16)
    rid = models.CharField(verbose_name=_('클라이언트 ID'), max_length=60)
    username = models.CharField(verbose_name=_('시스템 사용자명'), max_length=20)
    hostname = models.CharField(verbose_name=_('운영체제명'), max_length=30)
    alias = models.CharField(verbose_name=_('별칭'), max_length=30)
    platform = models.CharField(verbose_name=_('플랫폼'), max_length=30)
    tags = models.CharField(verbose_name=_('태그'), max_length=30)
    rhash = models.CharField(verbose_name=_('기기 연결 비밀번호'), max_length=60)

    class Meta:
        ordering = ('-username',)
        verbose_name = "Peers"
        verbose_name_plural = _("Peers 목록")


class RustDeskPeerAdmin(admin.ModelAdmin):
    list_display = ('rid', 'uid', 'username', 'hostname', 'platform', 'alias', 'tags')
    search_fields = ('deviceid', 'alias')
    list_filter = ('rid', 'uid', )


class RustDesDevice(models.Model):
    rid = models.CharField(verbose_name=_('클라이언트 ID'), max_length=60, blank=True)
    cpu = models.CharField(verbose_name='CPU', max_length=100)
    hostname = models.CharField(verbose_name=_('호스트명'), max_length=100)
    memory = models.CharField(verbose_name=_('메모리'), max_length=100)
    os = models.CharField(verbose_name=_('운영체제'), max_length=100)
    uuid = models.CharField(verbose_name='uuid', max_length=100)
    username = models.CharField(verbose_name=_('시스템 사용자명'), max_length=100, blank=True)
    version = models.CharField(verbose_name=_('클라이언트 버전'), max_length=100)
    ip_address = models.CharField(verbose_name=_('IP'), max_length=60, blank=True)
    create_time = models.DateTimeField(verbose_name=_('기기 등록 시간'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=('기기 업데이트 시간'), auto_now=True, blank=True)

    class Meta:
        ordering = ('-rid',)
        verbose_name = _("기기")
        verbose_name_plural = _("기기 목록")


class RustDesDeviceAdmin(admin.ModelAdmin):
    list_display = ('rid', 'hostname', 'memory', 'uuid', 'version', 'create_time', 'update_time')
    search_fields = ('hostname', 'memory')
    list_filter = ('rid', )


class ConnLog(models.Model):
    id = models.IntegerField(verbose_name='ID', primary_key=True)
    action = models.CharField(verbose_name='Action', max_length=20, null=True)
    conn_id = models.CharField(verbose_name='Connection ID', max_length=10, null=True)
    from_ip = models.CharField(verbose_name='From IP', max_length=30, null=True)
    from_id = models.CharField(verbose_name='From ID', max_length=20, null=True)
    rid = models.CharField(verbose_name='To ID', max_length=20, null=True)
    conn_start = models.DateTimeField(verbose_name='Connected', null=True)
    conn_end = models.DateTimeField(verbose_name='Disconnected', null=True)
    session_id = models.CharField(verbose_name='Session ID', max_length=60, null=True)
    uuid = models.CharField(verbose_name='uuid', max_length=60, null=True)


class ConnLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'conn_id', 'from_ip', 'from_id', 'rid', 'conn_start', 'conn_end', 'session_id', 'uuid')
    search_fields = ('from_ip', 'rid')
    list_filter = ('id', 'from_ip', 'from_id', 'rid', 'conn_start', 'conn_end')


class FileLog(models.Model):
    id = models.IntegerField(verbose_name='ID', primary_key=True)
    file = models.CharField(verbose_name='Path', max_length=500)
    remote_id = models.CharField(verbose_name='Remote ID', max_length=20, default='0')
    user_id = models.CharField(verbose_name='User ID', max_length=20, default='0')
    user_ip = models.CharField(verbose_name='User IP', max_length=20, default='0')
    filesize = models.CharField(verbose_name='Filesize', max_length=500, default='')
    direction = models.IntegerField(verbose_name='Direction', default=0)
    logged_at = models.DateTimeField(verbose_name='Logged At', null=True)


class FileLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'remote_id', 'user_id', 'user_ip', 'filesize', 'direction', 'logged_at')
    search_fields = ('file', 'remote_id', 'user_id', 'user_ip')
    list_filter = ('id', 'file', 'remote_id', 'user_id', 'user_ip', 'filesize', 'direction', 'logged_at')


class ShareLink(models.Model):
    ''' 分享链接
    '''
    uid = models.CharField(verbose_name=_('사용자 ID'), max_length=16)
    shash = models.CharField(verbose_name=_('링크 Key'), max_length=60)
    peers = models.CharField(verbose_name=_('기기 ID 목록'), max_length=20)
    is_used = models.BooleanField(verbose_name=_('사용 여부'), default=False)
    is_expired = models.BooleanField(verbose_name=_('만료 여부'), default=False)
    create_time = models.DateTimeField(verbose_name=_('생성 시간'), auto_now_add=True)

    class Meta:
        ordering = ('-create_time',)
        verbose_name = _("공유 링크")
        verbose_name_plural = _("링크 목록")


class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ('shash', 'uid', 'peers', 'is_used', 'is_expired', 'create_time')
    search_fields = ('peers', )
    list_filter = ('is_used', 'uid', 'is_expired')
