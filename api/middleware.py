# cython:language_level=3
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from django.contrib.auth import login
from django.conf import settings
from api.models_user import UserProfile
from api.models_work import RustDeskToken


class TokenAutoLoginMiddleware:
    """
    URL 파라미터 ?token=... 을 통한 자동 로그인 미들웨어
    앱에서 웹사이트로 이동 시 별도 로그인 없이 인증
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 이미 로그인되어 있으면 스킵
        if request.user.is_authenticated:
            return self.get_response(request)
        
        # URL 파라미터에서 토큰 확인
        token_param = request.GET.get('token', '')
        
        if token_param:
            # 토큰으로 사용자 찾기
            token_obj = RustDeskToken.objects.filter(access_token=token_param).first()
            if token_obj:
                user = UserProfile.objects.filter(id=token_obj.uid).first()
                if user and user.is_active:
                    # Django 세션에 로그인 처리
                    login(request, user)
                    print(f"[AUTO_LOGIN] 토큰 자동 로그인 성공: {user.username}")
        
        response = self.get_response(request)
        return response


class AdminSubdomainMiddleware:
    """
    admin.787.kr로만 접근 가능하도록 제한하는 미들웨어
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # 보호할 경로 목록 (다운로드는 제외)
        self.protected_paths = [
            '/api/user_action',
            '/api/work',
            '/api/share',
            '/api/conn_log',
            '/api/file_log',
            '/api/down_peers',
        ]

    def __call__(self, request):
        # 보호할 경로인지 확인
        path = request.path
        is_protected = any(path.startswith(protected) for protected in self.protected_paths)
        
        if is_protected:
            host = request.get_host()
            # admin.787.kr 또는 admin.localhost로 시작하지 않으면 /default로 리다이렉트
            admin_host = getattr(settings, 'ID_SERVER', 'admin.787.kr')
            if not (host.startswith(admin_host) or host.startswith('admin.localhost')):
                return HttpResponseRedirect('/default')
        
        # /api/custom_app의 경우 뷰에서 처리 (다운로드는 공개, 저장은 admin만)
        if path.startswith('/api/custom_app'):
            host = request.get_host()
            admin_host = getattr(settings, 'ID_SERVER', 'admin.787.kr')
            # GET 요청(설정 페이지)은 admin 도메인에서만 접근 가능
            if request.method == 'GET' and not (host.startswith(admin_host) or host.startswith('admin.localhost')):
                return HttpResponseRedirect('/default')
            # POST 요청은 뷰에서 action에 따라 처리
        
        response = self.get_response(request)
        return response

