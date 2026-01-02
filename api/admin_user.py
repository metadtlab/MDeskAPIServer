# cython:language_level=3
from django.contrib import admin
from api import models
from django import forms
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import gettext as _
import datetime


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""
    password1 = forms.CharField(label=_('비밀번호'), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_('비밀번호 재입력'), widget=forms.PasswordInput)

    class Meta:
        model = models.UserProfile
        fields = ('username','is_active','is_admin')

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("비밀번호 확인 실패, 두 비밀번호가 일치하지 않습니다."))
        return password2

    
    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField(label=(_("비밀번호 Hash 값")), help_text=("<a href=\"../password/\">비밀번호 변경</a>."))
    class Meta:
        model = models.UserProfile
        fields = ('username', 'is_active', 'is_admin')

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]
        #return self.initial["password"]
    
    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserChangeForm, self).save(commit=False)
        
        if commit:
            user.save()
        return user

class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm
    password = ReadOnlyPasswordHashField(label=("비밀번호 Hash 값"), help_text=("<a href=\"../password/\">비밀번호 변경</a>."))
    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ('username', 'rid', 'membership_level', 'membership_expires', 'max_agents', 'is_active')
    list_filter = ('is_admin', 'is_active', 'membership_level')
    fieldsets = (
        (_('기본 정보'), {'fields': ('username', 'password', 'is_active', 'is_admin', 'rid', 'uuid', 'deviceInfo',)}),
        (_('연락처 정보'), {'fields': ('company_name', 'email', 'phone', 'phone_verified',)}),
        (_('회원 등급'), {'fields': ('membership_level', 'membership_start', 'membership_expires', 'max_agents',)}),
    )
    readonly_fields = ('rid', 'uuid')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username',  'is_active', 'is_admin', 'password1', 'password2',  )}
         ),
    )
    
    search_fields = ('username', )
    ordering = ('username',)
    filter_horizontal = ()


class AgentConnectionLogAdmin(admin.ModelAdmin):
    """상담원 접속 기록 Admin"""
    list_display = ('uid', 'mdesk_id', 'agent_num', 'create_time')
    list_filter = ('uid', 'agent_num', 'create_time')
    search_fields = ('mdesk_id', 'uid__username')
    readonly_fields = ('create_time',)
    
    def get_queryset(self, request):
        """현재 시간 기준 10분 이내 데이터만 표시"""
        qs = super().get_queryset(request)
        now = datetime.datetime.now()
        ten_minutes_ago = now - datetime.timedelta(minutes=10)
        return qs.filter(create_time__gte=ten_minutes_ago)


class GroupAdmin(admin.ModelAdmin):
    """그룹 관리 Admin"""
    list_display = ('company_name', 'contact_name', 'contact_phone', 'is_active', 'is_deleted', 'create_time')
    list_filter = ('is_active', 'is_deleted', 'create_time', 'uid')
    search_fields = ('company_name', 'business_number', 'contact_name', 'contact_phone', 'address')
    readonly_fields = ('create_time', 'update_time', 'deleted_at')
    fieldsets = (
        (_('기본 정보'), {'fields': ('uid', 'company_name', 'business_number', 'representative', 'is_active')}),
        (_('담당자 정보'), {'fields': ('contact_name', 'contact_phone', 'contact_email')}),
        (_('주소'), {'fields': ('address', 'address_detail')}),
        (_('기타'), {'fields': ('memo', 'create_time', 'update_time')}),
        (_('삭제 정보'), {'fields': ('is_deleted', 'deleted_at'), 'classes': ('collapse',)}),
    )
    
    actions = ['restore_groups']
    
    def restore_groups(self, request, queryset):
        """삭제된 그룹 복원"""
        restored = queryset.filter(is_deleted=True).update(is_deleted=False, deleted_at=None)
        self.message_user(request, _('{}개의 그룹이 복원되었습니다.').format(restored))
    restore_groups.short_description = _('선택한 그룹 복원')


admin.site.register(models.UserProfile, UserAdmin)
admin.site.register(models.RustDeskToken, models.RustDeskTokenAdmin)
admin.site.register(models.RustDeskTag, models.RustDeskTagAdmin)
admin.site.register(models.RustDeskPeer, models.RustDeskPeerAdmin)
admin.site.register(models.RustDesDevice, models.RustDesDeviceAdmin)
admin.site.register(models.ShareLink, models.ShareLinkAdmin)
admin.site.register(models.ConnLog, models.ConnLogAdmin)
admin.site.register(models.FileLog, models.FileLogAdmin)
admin.site.register(models.CustomAppConfig)
admin.site.register(models.AgentConnectionLog, AgentConnectionLogAdmin)
admin.site.register(models.Group, GroupAdmin)
admin.site.unregister(Group)
admin.site.site_header = _('RustDesk 자체 구축 Web')
admin.site.site_title = _('RustDesk 관리자')