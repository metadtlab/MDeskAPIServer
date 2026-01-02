import django
if django.__version__.split('.')[0]>='4':
    from django.urls import re_path as url
else:
    from django.conf.urls import  url, include

from api import views
 
urlpatterns = [
    url(r'^login',views.login),
    url(r'^logout',views.logout),
    url(r'^ab$',views.ab),
    url(r'^ab\/get',views.ab_get), # 兼容 x86-sciter 版客户端
    url(r'^users',views.users),
    url(r'^peers',views.peers),
    url(r'^device-group/accessible',views.device_group_accessible),  # RustDesk device-group accessible API
    url(r'^group$',views.group),  # RustDesk 그룹 API
    url(r'^groups',views.device_groups),  # RustDesk device groups API
    url(r'^currentUser',views.currentUser),
    url(r'^userInfo',views.userInfo),  # 로그인 사용자 정보 새로고침 API
    url(r'^sysinfo',views.sysinfo),
    url(r'^heartbeat',views.heartbeat),
    #url(r'^register',views.register), 
    url(r'^user_action',views.user_action),  # 前端
    url(r'^work',views.work),                # 前端
    url(r'^down_peers$',views.down_peers),   # 前端
    url(r'^share',views.share),              # 前端
    url(r'^conn_log',views.conn_log),
    url(r'^file_log',views.file_log),
    url(r'^audit',views.audit),
    url(r'^agentnumupdate/(?P<userid>[\w.@+-]+)/(?P<mdeskid>[\w.@+-]+)$', views.update_agent_connection), # 상담원 접속 정보 업데이트 API
    url(r'^agentclose/(?P<userid>[\w.@+-]+)/(?P<agentid>\d+)$', views.agent_close), # 클라이언트 종료 시 상담원 삭제 API
    url(r'^custom_app_config',views.custom_app_config),  # 커스텀 앱 설정 API (RustDesk 클라이언트용) - 순서 중요!
    url(r'^version/latest$',views.app_version),  # MDesk 실행파일 버전 정보 API
    url(r'^version/upload$',views.upload_executable),  # MDesk 실행파일 업로드 API
    url(r'^(?P<username>[\w.@+-]+)/addnum$', views.add_support_agent),  # 상담원 추가 API
    url(r'^(?P<username>[\w.@+-]+)/delnum/(?P<agent_num>\d+)$', views.delete_support_agent), # 상담원 삭제 API
    url(r'^(?P<username>[\w.@+-]+)/agents$', views.get_support_agents), # 상담원 목록 조회 API
    url(r'^custom_app',views.custom_app),  # 커스텀 앱 설정 (웹 UI)
    url(r'^group_manage$',views.group_manage),  # 그룹관리 (웹 UI)
    url(r'^group_manage/save$',views.group_save),  # 그룹 저장 API
    url(r'^group_manage/delete/(?P<group_id>\d+)$',views.group_delete),  # 그룹 삭제 API
    url(r'^user_manage$',views.user_manage),  # 사용자관리 (웹 UI)
    url(r'^user_manage/save$',views.user_manage_save),  # 사용자 저장 API
    url(r'^user_manage/delete/(?P<user_id>\d+)$',views.user_manage_delete),  # 사용자 삭제 API
    url(r'^user_manage/toggle_admin/(?P<user_id>\d+)$',views.user_toggle_admin),  # 관리자 권한 토글 API
    url(r'^team_member/add$',views.team_member_add),  # 팀원 추가 API
    url(r'^team_member/delete/(?P<member_id>\d+)$',views.team_member_delete),  # 팀원 삭제 API
    ]
