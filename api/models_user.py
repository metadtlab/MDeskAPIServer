# cython:language_level=3
from django.db import models
from django.contrib.auth.models import (
    BaseUserManager,AbstractBaseUser,PermissionsMixin
)
from .models_work import *
from django.utils.translation import gettext as _

class MyUserManager(BaseUserManager):
    def create_user(self, username, password=None):
        if not username:
            raise ValueError('Users must have an username')

        user = self.model(username=username,
        )
 
        user.set_password(password)
        user.save(using=self._db)
        return user
 
    def create_superuser(self, username, password):
        user = self.create_user(username,
            password=password,
            
        )
        user.is_admin = True
        user.save(using=self._db)
        return user


class UserProfile(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(_('사용자명'), 
                                unique=True,
                                max_length=50)
    
    rid = models.CharField(verbose_name='MDesk ID', max_length=16, blank=True, default='')
    uuid = models.CharField(verbose_name='uuid', max_length=60, blank=True, default='')
    autoLogin = models.BooleanField(verbose_name='autoLogin', default=True)
    rtype = models.CharField(verbose_name='rtype', max_length=20, blank=True, default='')
    deviceInfo = models.TextField(verbose_name=_('로그인 정보:'), blank=True)
    
    company_name = models.CharField(verbose_name=_('회사명'), max_length=100, blank=True, default='')
    group_id = models.IntegerField(verbose_name=_('그룹 ID'), null=True, blank=True)
    email = models.EmailField(verbose_name=_('이메일'), blank=True, default='')
    phone = models.CharField(verbose_name=_('휴대전화'), max_length=20, blank=True, default='')
    phone_verified = models.BooleanField(verbose_name=_('휴대전화 인증 여부'), default=False)
    
    # 유료 사용자 등급 관리
    MEMBERSHIP_CHOICES = [
        ('free', '무료'),
        ('basic', '기본'),
        ('standard', '스탠다드'),
        ('premium', '프리미엄'),
        ('enterprise', '엔터프라이즈'),
    ]
    membership_level = models.CharField(
        verbose_name=_('회원 등급'),
        max_length=20,
        choices=MEMBERSHIP_CHOICES,
        default='free'
    )
    membership_start = models.DateField(verbose_name=_('이용 시작일'), blank=True, null=True)
    membership_expires = models.DateField(verbose_name=_('이용 만료일'), blank=True, null=True)
    max_agents = models.IntegerField(verbose_name=_('최대 상담원 수'), default=3)
    
    is_active = models.BooleanField(verbose_name=_('활성화 여부'), default=True)
    is_admin = models.BooleanField(verbose_name=_('관리자 여부'), default=False)

    objects = MyUserManager()
 
    USERNAME_FIELD = 'username'  # 用作用户名的字段
    REQUIRED_FIELDS = ['password']     #必须填写的字段
    
    
    def get_full_name(self):
        # The user is identified by their email address
        return self.username
 
    def get_short_name(self):
        # The user is identified by their email address
        return self.username
 
    def __str__(self):              # __unicode__ on Python 2
        return self.username
 
    def has_perm(self, perm, obj=None):    #有没有指定的权限
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True
 
    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True
        


    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff 
        return self.is_admin

    class Meta:
    
        verbose_name = _("사용자")
        verbose_name_plural = _("사용자 목록")
        permissions = (
            ("view_task", "Can see available tasks"),
            ("change_task_status", "Can change the status of tasks"),
            ("close_task", "Can remove a task by setting its status as closed"),
        )


def logo_upload_path(instance, filename):
    """로고 파일 업로드 경로 생성 - uid 기반으로 중복되지 않는 파일명 생성"""
    import time
    
    # 파일 확장자 추출 (소문자로 변환)
    ext = filename.split('.')[-1].lower() if '.' in filename else 'jpg'
    # 지원되는 이미지 확장자만 허용
    if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        ext = 'jpg'
    
    # uid 확인 (instance가 저장되지 않은 경우 대비)
    try:
        uid = instance.uid.id if instance.uid and instance.uid.id else 'temp'
    except:
        uid = 'temp'
    
    # uid_타임스탬프.확장자 형식으로 저장 (중복 방지, 한글 문제 없음)
    # 매번 업로드할 때마다 새로운 파일명으로 저장됨
    timestamp = int(time.time() * 1000)  # 밀리초 단위로 더 정확하게
    return f'custom_logos/{uid}_{timestamp}.{ext}'


class CustomAppConfig(models.Model):
    """커스텀 앱 설정"""
    uid = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name=_('사용자'))
    app_name = models.CharField(verbose_name=_('앱 이름'), max_length=100, default='MDesk')
    logo = models.ImageField(verbose_name=_('로고'), upload_to=logo_upload_path, blank=True, null=True)
    password = models.CharField(verbose_name=_('암호'), max_length=100, blank=True, default='')
    title = models.CharField(verbose_name=_('제목'), max_length=200, default='Your Desktop', blank=True)
    description = models.CharField(verbose_name=_('설명'), max_length=500, default='Your desktop can be accessed with this ID and password.', blank=True)
    phone = models.CharField(verbose_name=_('전화번호'), max_length=20, blank=True, default='')
    url_nickname = models.CharField(verbose_name=_('URL 별명'), max_length=50, blank=True, default=None, unique=True, null=True)
    create_time = models.DateTimeField(verbose_name=_('생성 시간'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('수정 시간'), auto_now=True)

    class Meta:
        verbose_name = _("커스텀 앱 설정")
        verbose_name_plural = _("커스텀 앱 설정 목록")
        unique_together = ('uid',)

class SupportAgent(models.Model):
    """상담원 목록"""
    uid = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name=_('사용자'))
    agent_num = models.IntegerField(verbose_name=_('상담원 번호'))
    agent_name = models.CharField(verbose_name=_('상담원 이름'), max_length=100)
    create_time = models.DateTimeField(verbose_name=_('생성 시간'), auto_now_add=True)

    class Meta:
        verbose_name = _("상담원")
        verbose_name_plural = _("상담원 목록")
        unique_together = ('uid', 'agent_num')
        ordering = ['agent_num']

    def __str__(self):
        return f"{self.uid.username} - {self.agent_name}"

class AgentConnectionLog(models.Model):
    """상담원 접속 기록"""
    uid = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name=_('사용자'))
    mdesk_id = models.CharField(verbose_name=_('MDesk ID'), max_length=50)
    agent_num = models.IntegerField(verbose_name=_('상담원 번호'))
    create_time = models.DateTimeField(verbose_name=_('접속 시간'), auto_now_add=True)

    class Meta:
        verbose_name = _("상담원 접속 기록")
        verbose_name_plural = _("상담원 접속 기록 목록")
        ordering = ['-create_time']


class Group(models.Model):
    """그룹(거래처) 정보"""
    uid = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name=_('소유자'), related_name='owned_groups')
    company_name = models.CharField(verbose_name=_('회사명'), max_length=200)
    business_number = models.CharField(verbose_name=_('사업자번호'), max_length=20, blank=True, default='')
    representative = models.CharField(verbose_name=_('대표자명'), max_length=50, blank=True, default='')
    contact_name = models.CharField(verbose_name=_('담당자 이름'), max_length=50, blank=True, default='')
    contact_phone = models.CharField(verbose_name=_('담당자 전화번호'), max_length=20, blank=True, default='')
    contact_email = models.EmailField(verbose_name=_('담당자 이메일'), blank=True, default='')
    address = models.CharField(verbose_name=_('주소'), max_length=300, blank=True, default='')
    address_detail = models.CharField(verbose_name=_('상세주소'), max_length=200, blank=True, default='')
    memo = models.TextField(verbose_name=_('메모'), blank=True, default='')
    is_active = models.BooleanField(verbose_name=_('활성화'), default=True)
    is_deleted = models.BooleanField(verbose_name=_('삭제됨'), default=False)
    deleted_at = models.DateTimeField(verbose_name=_('삭제일'), null=True, blank=True)
    create_time = models.DateTimeField(verbose_name=_('등록일'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('수정일'), auto_now=True)

    class Meta:
        verbose_name = _("그룹")
        verbose_name_plural = _("그룹 목록")
        ordering = ['-create_time']

    def __str__(self):
        return self.company_name
    
    def soft_delete(self):
        """소프트 삭제"""
        import datetime
        self.is_deleted = True
        self.deleted_at = datetime.datetime.now()
        self.save()


class TeamMember(models.Model):
    """팀원(직원) 정보 - 사용자가 관리하는 직원 목록"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name=_('소유자'), related_name='team_members')
    name = models.CharField(verbose_name=_('이름'), max_length=50)
    phone = models.CharField(verbose_name=_('전화번호'), max_length=20, blank=True, default='')
    memo = models.CharField(verbose_name=_('메모'), max_length=200, blank=True, default='')
    is_active = models.BooleanField(verbose_name=_('활성화'), default=True)
    create_time = models.DateTimeField(verbose_name=_('등록일'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('수정일'), auto_now=True)

    class Meta:
        verbose_name = _("팀원")
        verbose_name_plural = _("팀원 목록")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.phone})"

