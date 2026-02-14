# cython:language_level=3
from django.http import JsonResponse, FileResponse, Http404
import json
import time
import datetime
# import hashlib
import math
from django.contrib import auth
# from django.forms.models import model_to_dict
from api.models import RustDeskToken, UserProfile, RustDeskTag, RustDeskPeer, RustDesDevice, ConnLog, FileLog, CustomAppConfig, SupportAgent, AgentConnectionLog, RelayServer, RemoteAuthLog, MdeskDeviceRegistration, CertNoVerification
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import copy
from .views_front import *
from django.utils.translation import gettext as _
from django.core.cache import cache


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def _generate_2fa_code():
    """6자리 2FA 인증코드 생성"""
    import random
    return str(random.randint(100000, 999999))


def _send_2fa_email(email, code, username):
    """2FA 인증코드 이메일 발송"""
    from django.core.mail import send_mail
    from django.conf import settings
    try:
        subject = 'MDesk 로그인 2차 인증코드'
        message = f"""안녕하세요, {username}님.

MDesk 로그인 2차 인증코드입니다.

인증코드: {code}

이 인증코드는 5분간 유효합니다.
본인이 로그인을 시도하지 않았다면, 비밀번호를 즉시 변경해주세요.

감사합니다.
MDesk 원격지원"""
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        print(f"[2FA 이메일] 발송 성공: {username} ({email})")
        return True
    except Exception as e:
        print(f"[2FA 이메일] 발송 실패: {str(e)}")
        return False


def _send_2fa_sms(phone, code, username):
    """2FA 인증코드 카카오 알림톡 발송"""
    try:
        send_kakao_alimtalk(phone, code)
        print(f"[2FA 알림톡] 발송 성공: {username} ({phone})")
        return True
    except Exception as e:
        print(f"[2FA 알림톡] 발송 실패: {str(e)}")
        return False


def _complete_login(user, rid, uuid):
    """로그인 완료 처리: 디바이스 바인딩 + 토큰 발급 + 응답 생성"""
    # 디바이스 바인딩
    peer = RustDeskPeer.objects.filter(Q(rid=rid)).first()
    if not peer:
        device = RustDesDevice.objects.filter(Q(uuid=uuid)).first()
        if device:
            peer = RustDeskPeer()
            peer.uid = user.id
            peer.rid = device.rid
            peer.hostname = device.hostname
            peer.username = device.username
            peer.save()

    token = RustDeskToken.objects.filter(Q(uid=user.id) & Q(username=user.username) & Q(rid=user.rid)).first()

    # 토큰 만료 확인
    if token:
        now_t = datetime.datetime.now()
        nums = (now_t - token.create_time).seconds if now_t > token.create_time else 0
        if nums >= EFFECTIVE_SECONDS:
            token.delete()
            token = None

    if not token:
        token = RustDeskToken(
            username=user.username,
            uid=user.id,
            uuid=user.uuid,
            rid=user.rid,
            access_token=getStrMd5(str(time.time()) + salt)
        )
        token.save()

    # 릴레이 서버 퍼블릭 키 조회
    relay_pub_key = ''
    if user.relay_server:
        rs = RelayServer.objects.filter(server_address=user.relay_server).first()
        if rs:
            relay_pub_key = rs.public_key

    result = {
        'access_token': token.access_token,
        'type': 'access_token',
        'user': {
            'user_pkid': user.id,
            'name': user.username,
            'email': user.email,
            'phone': user.phone,
            'company_name': user.company_name,
            'membership_level': user.membership_level,
            'membership_start': user.membership_start.isoformat() if user.membership_start else None,
            'membership_expires': user.membership_expires.isoformat() if user.membership_expires else None,
            'max_agents': user.max_agents,
            'relay_server': user.relay_server,
            'relay_pub_key': relay_pub_key,
            'is_admin': user.is_admin,
        }
    }
    return result


def login(request):
    result = {}
    if request.method == 'GET':
        result['error'] = _('요청 방식 오류! POST 방식을 사용하세요.')
        return JsonResponse(result)

    data = json.loads(request.body.decode())

    username = data.get('username', '')
    password = data.get('password', '')
    rid = data.get('id', '')
    uuid = data.get('uuid', '')
    autoLogin = data.get('autoLogin', True)
    rtype = data.get('type', '')
    deviceInfo = data.get('deviceInfo', '')
    user = auth.authenticate(username=username, password=password)
    if not user:
        result['error'] = _('계정 또는 비밀번호가 틀렸습니다! 다시 시도하세요. 여러 번 시도하면 IP가 차단됩니다!')
        return JsonResponse(result)
    user.rid = rid
    user.uuid = uuid
    user.autoLogin = autoLogin
    user.rtype = rtype
    user.deviceInfo = json.dumps(deviceInfo)
    user.save()

    # ===== 2차 인증(2FA) 확인 =====
    tfa_required = getattr(user, 'email_2fa', False) or getattr(user, 'phone_2fa', False)
    
    if tfa_required:
        # 2FA 인증코드 생성 및 캐시 저장 (5분 유효)
        code = _generate_2fa_code()
        tfa_key = f'2fa_{user.id}_{rid}'
        cache.set(tfa_key, {
            'code': code,
            'user_id': user.id,
            'rid': rid,
            'uuid': uuid,
            'attempts': 0,
        }, timeout=300)  # 5분
        
        # 2FA 방식에 따라 인증코드 발송
        sent_methods = []
        if getattr(user, 'email_2fa', False) and user.email:
            if _send_2fa_email(user.email, code, user.username):
                # 이메일 마스킹 (예: te***@gmail.com)
                email_parts = user.email.split('@')
                masked = email_parts[0][:2] + '***@' + email_parts[1]
                sent_methods.append({'type': 'email', 'target': masked})
        
        if getattr(user, 'phone_2fa', False) and user.phone:
            if _send_2fa_sms(user.phone, code, user.username):
                # 전화번호 마스킹 (예: 010****5678)
                phone_clean = user.phone.replace('-', '')
                masked = phone_clean[:3] + '****' + phone_clean[-4:]
                sent_methods.append({'type': 'phone', 'target': masked})
        
        if not sent_methods:
            # 발송 실패 시 2FA 건너뛰고 로그인 완료
            print(f"[2FA] 인증코드 발송 실패, 2FA 건너뜀: {user.username}")
            cache.delete(tfa_key)
        else:
            # 2FA 필요 응답 반환
            result['tfa_required'] = True
            result['tfa_key'] = tfa_key
            result['tfa_methods'] = sent_methods
            result['tfa_message'] = _('2차 인증이 필요합니다. 발송된 인증코드를 입력해주세요.')
            return JsonResponse(result)
    
    # 2FA 불필요 또는 발송 실패 시 바로 로그인 완료
    result = _complete_login(user, rid, uuid)
    return JsonResponse(result)


def login_2fa_verify(request):
    """2차 인증코드 검증 API"""
    result = {}
    if request.method == 'GET':
        result['error'] = _('요청 방식 오류! POST 방식을 사용하세요.')
        return JsonResponse(result)
    
    data = json.loads(request.body.decode())
    tfa_key = data.get('tfa_key', '')
    tfa_code = data.get('tfa_code', '')
    
    if not tfa_key or not tfa_code:
        result['error'] = _('인증코드와 인증 키가 필요합니다.')
        return JsonResponse(result)
    
    # 캐시에서 2FA 정보 조회
    tfa_data = cache.get(tfa_key)
    if not tfa_data:
        result['error'] = _('인증코드가 만료되었습니다. 다시 로그인해주세요.')
        return JsonResponse(result)
    
    # 시도 횟수 확인 (최대 5회)
    if tfa_data.get('attempts', 0) >= 5:
        cache.delete(tfa_key)
        result['error'] = _('인증 시도 횟수를 초과했습니다. 다시 로그인해주세요.')
        return JsonResponse(result)
    
    # 인증코드 검증
    if tfa_code != tfa_data['code']:
        tfa_data['attempts'] = tfa_data.get('attempts', 0) + 1
        cache.set(tfa_key, tfa_data, timeout=300)
        remaining = 5 - tfa_data['attempts']
        result['error'] = _('인증코드가 일치하지 않습니다. (남은 시도: {}회)').format(remaining)
        return JsonResponse(result)
    
    # 인증 성공 - 캐시 삭제
    cache.delete(tfa_key)
    
    # 사용자 조회 및 로그인 완료
    user = UserProfile.objects.filter(id=tfa_data['user_id']).first()
    if not user:
        result['error'] = _('사용자를 찾을 수 없습니다.')
        return JsonResponse(result)
    
    result = _complete_login(user, tfa_data['rid'], tfa_data['uuid'])
    return JsonResponse(result)


def logout(request):
    if request.method == 'GET':
        result = {'error': _('요청 방식 오류!')}
        return JsonResponse(result)

    data = json.loads(request.body.decode())
    rid = data.get('id', '')
    uuid = data.get('uuid', '')
    user = UserProfile.objects.filter(Q(rid=rid) & Q(uuid=uuid)).first()
    if not user:
        result = {'error': _('비정상적인 요청!')}
        return JsonResponse(result)
    token = RustDeskToken.objects.filter(Q(uid=user.id) & Q(rid=user.rid)).first()
    if token:
        token.delete()

    result = {'code': 1}
    return JsonResponse(result)


def currentUser(request):
    result = {}
    if request.method == 'GET':
        result['error'] = _('잘못된 제출 방식!')
        return JsonResponse(result)
    # postdata = json.loads(request.body)
    # rid = postdata.get('id', '')
    # uuid = postdata.get('uuid', '')

    access_token = request.META.get('HTTP_AUTHORIZATION', '')
    access_token = access_token.split('Bearer ')[-1]
    
    if not access_token:
        result['error'] = _('인증 토큰이 필요합니다.')
        return JsonResponse(result, status=401)
    
    token = RustDeskToken.objects.filter(Q(access_token=access_token)).first()
    if not token:
        result['error'] = _('유효하지 않은 토큰입니다.')
        return JsonResponse(result, status=401)
    
    user = UserProfile.objects.filter(Q(id=token.uid)).first()
    if not user:
        result['error'] = _('사용자를 찾을 수 없습니다.')
        return JsonResponse(result, status=401)

    result['access_token'] = token.access_token
    result['type'] = 'access_token'
    result['name'] = user.username
    return JsonResponse(result)


def userInfo(request):
    """
    로그인 사용자 정보 새로고침 API
    Bearer 토큰 인증 사용
    
    반환: 멤버십 정보, 연락처, 회사명 등
    """
    result = {}
    
    # 토큰 확인
    access_token = request.META.get('HTTP_AUTHORIZATION', '')
    access_token = access_token.split('Bearer ')[-1]
    
    if not access_token:
        result['error'] = _('인증 토큰이 필요합니다.')
        return JsonResponse(result, status=401)
    
    token = RustDeskToken.objects.filter(Q(access_token=access_token)).first()
    if not token:
        result['error'] = _('유효하지 않은 토큰입니다.')
        return JsonResponse(result, status=401)
    
    user = UserProfile.objects.filter(Q(id=token.uid)).first()
    if not user:
        result['error'] = _('사용자를 찾을 수 없습니다.')
        return JsonResponse(result, status=404)
    
    # 릴레이 서버 퍼블릭 키 조회
    relay_pub_key = ''
    if user.relay_server:
        rs = RelayServer.objects.filter(server_address=user.relay_server).first()
        if rs:
            relay_pub_key = rs.public_key

    # 사용자 정보 반환
    result['code'] = 1
    result['data'] = {
        'user_pkid': user.id,
        'username': user.username,
        'email': user.email,
        'phone': user.phone,
        'company_name': user.company_name,
        'membership_level': user.membership_level,
        'membership_start': user.membership_start.isoformat() if user.membership_start else None,
        'membership_expires': user.membership_expires.isoformat() if user.membership_expires else None,
        'max_agents': user.max_agents,
        'relay_server': user.relay_server,
        'relay_pub_key': relay_pub_key,
        'is_admin': user.is_admin,
        'is_active': user.is_active,
    }
    return JsonResponse(result)


def ab(request):
    '''
    '''
    access_token = request.META.get('HTTP_AUTHORIZATION', '')
    access_token = access_token.split('Bearer ')[-1]
    
    if not access_token:
        result = {'error': _('인증 토큰이 필요합니다.')}
        return JsonResponse(result, status=401)
    
    token = RustDeskToken.objects.filter(Q(access_token=access_token)).first()
    if not token:
        result = {'error': _('유효하지 않은 토큰입니다.')}
        return JsonResponse(result, status=401)

    if request.method == 'GET':
        result = {}
        uid = token.uid
        tags = RustDeskTag.objects.filter(Q(uid=uid))
        tag_names = []
        tag_colors = {}
        if tags:
            tag_names = [str(x.tag_name) for x in tags]
            tag_colors = {str(x.tag_name): int(x.tag_color) for x in tags if x.tag_color != ''}

        peers_result = []
        peers = RustDeskPeer.objects.filter(Q(uid=uid))
        if peers:
            for peer in peers:
                tmp = {
                    'id': peer.rid,
                    'username': peer.username,
                    'hostname': peer.hostname,
                    'alias': peer.alias,
                    'platform': peer.platform,
                    'tags': peer.tags.split(','),
                    'hash': peer.rhash,
                }
                peers_result.append(tmp)

        # RustDesk 클라이언트가 기대하는 형식으로 응답
        ab_data = {
            'peers': peers_result,
            'tags': tag_names,
            'tag_colors': tag_colors  # 객체 그대로 (이중 문자열화 방지)
        }
        result['data'] = json.dumps(ab_data)  # 전체를 한 번만 문자열화
        result['licensed_devices'] = 0
        return JsonResponse(result)
    else:
        postdata = json.loads(request.body.decode())
        data = postdata.get('data', '')
        data = {} if data == '' else json.loads(data)
        tagnames = data.get('tags', [])
        tag_colors = data.get('tag_colors', '')
        tag_colors = {} if tag_colors == '' else json.loads(tag_colors)
        peers = data.get('peers', [])

        if tagnames:
            # 删除旧的tag
            RustDeskTag.objects.filter(uid=token.uid).delete()
            # 增加新的
            newlist = []
            for name in tagnames:
                tag = RustDeskTag(
                    uid=token.uid,
                    tag_name=name,
                    tag_color=tag_colors.get(name, '')
                )
                newlist.append(tag)
            RustDeskTag.objects.bulk_create(newlist)
        if peers:
            RustDeskPeer.objects.filter(uid=token.uid).delete()
            newlist = []
            for one in peers:
                peer = RustDeskPeer(
                    uid=token.uid,
                    rid=one['id'],
                    username=one['username'],
                    hostname=one['hostname'],
                    alias=one['alias'],
                    platform=one['platform'],
                    tags=','.join(one['tags']),
                    rhash=one['hash'],


                )
                newlist.append(peer)
            RustDeskPeer.objects.bulk_create(newlist)

    result = {
        'code': 102,
        'data': _('주소록 업데이트 오류')
    }
    return JsonResponse(result)


def ab_get(request):
    # 兼容 x86-sciter 版客户端，此版客户端通过访问 "POST /api/ab/get" 来获取地址簿
    request.method = 'GET'
    return ab(request)


def ab_personal(request):
    '''RustDesk 개인 주소록 API - 404 반환하여 레거시 모드로 폴백'''
    from django.http import JsonResponse
    return JsonResponse({'error': 'Not implemented'}, status=404)


def ab_settings(request):
    '''RustDesk 주소록 설정 API'''
    access_token = request.META.get('HTTP_AUTHORIZATION', '')
    access_token = access_token.split('Bearer ')[-1]
    
    if not access_token:
        result = {'error': _('인증 토큰이 필요합니다.')}
        return JsonResponse(result, status=401)
    
    token = RustDeskToken.objects.filter(Q(access_token=access_token)).first()
    if not token:
        result = {'error': _('유효하지 않은 토큰입니다.')}
        return JsonResponse(result, status=401)
    
    # 주소록 설정 반환
    result = {
        'max_peer_one_ab': 0,  # 0 = 무제한
        'licensed_devices': 0,
    }
    return JsonResponse(result)


def sysinfo(request):
    # 客户端注册服务后，才会发送设备信息
    result = {}
    if request.method == 'GET':
        result['error'] = _('잘못된 제출 방식!')
        return JsonResponse(result)
    client_ip = get_client_ip(request)
    postdata = json.loads(request.body)
    device = RustDesDevice.objects.filter(Q(rid=postdata['id']) & Q(uuid=postdata['uuid'])).first()
    if not device:
        device = RustDesDevice(
            rid=postdata['id'],
            cpu=postdata['cpu'],
            hostname=postdata['hostname'],
            memory=postdata['memory'],
            os=postdata['os'],
            username=postdata.get('username', '-'),
            uuid=postdata['uuid'],
            version=postdata['version'],
            ip_address=client_ip
        )
        device.save()
    else:
        postdata2 = copy.copy(postdata)
        postdata2['rid'] = postdata2['id']
        postdata2.pop('id')
        RustDesDevice.objects.filter(Q(rid=postdata['id']) & Q(uuid=postdata['uuid'])).update(**postdata2)
    result['data'] = 'ok'
    return JsonResponse(result)


def heartbeat(request):
    result = {}
    
    # GET 요청 또는 빈 body인 경우 처리
    if request.method == 'GET' or not request.body:
        result['data'] = _('온라인')
        return JsonResponse(result)
    
    try:
        postdata = json.loads(request.body)
    except json.JSONDecodeError:
        result['data'] = _('온라인')
        return JsonResponse(result)
    
    device = RustDesDevice.objects.filter(Q(rid=postdata.get('id', '')) & Q(uuid=postdata.get('uuid', ''))).first()
    if device:
        client_ip = get_client_ip(request)
        device.ip_address = client_ip
        device.save()
    # token保活
    create_time = datetime.datetime.now() + datetime.timedelta(seconds=EFFECTIVE_SECONDS)
    RustDeskToken.objects.filter(Q(rid=postdata.get('id', '')) & Q(uuid=postdata.get('uuid', ''))).update(create_time=create_time)
    result['data'] = _('온라인')
    return JsonResponse(result)


def audit(request):
    """레거시 audit API - 모든 audit 요청 처리"""
    if request.method == 'GET' or not request.body:
        return JsonResponse({'code': 1, 'data': 'ok'})
    
    try:
        postdata = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 1, 'data': 'ok'})
    
    # print('audit:', postdata)
    audit_type = postdata.get('action', '')
    
    if audit_type == 'new':
        new_conn_log = ConnLog(
            action=postdata.get('action', ''),
            conn_id=postdata.get('conn_id', 0),
            from_ip=postdata.get('ip', ''),
            from_id='',
            rid=postdata.get('id', ''),
            conn_start=datetime.datetime.now(),
            session_id=postdata.get('session_id', 0),
            uuid=postdata.get('uuid', ''),
        )
        new_conn_log.save()
    elif audit_type == "close":
        ConnLog.objects.filter(Q(conn_id=postdata.get('conn_id'))).update(conn_end=datetime.datetime.now())
    elif 'is_file' in postdata:
        try:
            files = json.loads(postdata['info'])['files']
            filesize = convert_filesize(int(files[0][1]))
            new_file_log = FileLog(
                file=postdata.get('path', ''),
                user_id=postdata.get('peer_id', ''),
                user_ip=json.loads(postdata['info']).get('ip', ''),
                remote_id=postdata.get('id', ''),
                filesize=filesize,
                direction=postdata.get('type', ''),
                logged_at=datetime.datetime.now(),
            )
            new_file_log.save()
        except Exception as e:
            print('audit file error:', e)
    else:
        try:
            peer = postdata.get('peer', [])
            if peer:
                ConnLog.objects.filter(Q(conn_id=postdata.get('conn_id'))).update(
                    session_id=postdata.get('session_id', 0),
                    from_id=peer[0] if peer else ''
                )
        except Exception as e:
            print('audit error:', postdata, e)

    return JsonResponse({'code': 1, 'data': 'ok'})


def audit_conn(request):
    """연결 기록 API - /api/audit/conn"""
    if request.method == 'GET' or not request.body:
        return JsonResponse({'code': 1, 'data': 'ok'})
    
    try:
        postdata = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 1, 'data': 'ok'})
    
    print('audit_conn:', postdata)
    
    try:
        # 연결 시작
        action = postdata.get('action', '')
        if action == 'new':
            new_conn_log = ConnLog(
                action=action,
                conn_id=postdata.get('conn_id', 0),
                from_ip=postdata.get('ip', ''),
                from_id=postdata.get('from_id', ''),
                rid=postdata.get('id', ''),
                conn_start=datetime.datetime.now(),
                session_id=postdata.get('session_id', 0),
                uuid=postdata.get('uuid', ''),
            )
            new_conn_log.save()
        elif action == 'close':
            # 연결 종료
            ConnLog.objects.filter(Q(conn_id=postdata.get('conn_id'))).update(
                conn_end=datetime.datetime.now()
            )
        else:
            # peer 정보 업데이트
            peer = postdata.get('peer', [])
            if peer:
                ConnLog.objects.filter(Q(conn_id=postdata.get('conn_id'))).update(
                    session_id=postdata.get('session_id', 0),
                    from_id=peer[0] if isinstance(peer, list) and peer else str(peer)
                )
    except Exception as e:
        print('audit_conn error:', e)
    
    return JsonResponse({'code': 1, 'data': 'ok'})


def recent_sessions(request):
    """
    최근 연결 세션 조회 API
    
    엔드포인트: GET /api/sessions/recent
    쿼리 파라미터:
    - limit: 조회할 개수 (기본값: 10, 최대: 100)
    - user_pkid: 사용자 고유번호 (pk)로 필터링
    - username: 사용자명으로 필터링
    - client_id: 클라이언트 ID(from_id, rid)로 필터링
    
    응답:
    {
        "code": 1,
        "count": 10,
        "data": [
            {
                "id": 123,
                "from_id": "ABC123",
                "to_id": "DEF456",
                "from_ip": "192.168.0.1",
                "conn_start": "2026-01-18 22:30:00",
                "conn_end": "2026-01-18 22:35:00",
                "duration": "5분",
                "session_id": "xxx"
            },
            ...
        ]
    }
    """
    if request.method != 'GET':
        return JsonResponse({'code': 0, 'error': _('GET 요청만 허용됩니다.')}, status=405)
    
    # 쿼리 파라미터
    limit = request.GET.get('limit', '10')
    user_pkid = request.GET.get('user_pkid', '')
    username = request.GET.get('username', '')
    client_id = request.GET.get('client_id', '')
    
    try:
        limit = min(int(limit), 100)  # 최대 100개
    except ValueError:
        limit = 10
    
    # 최근 세션 조회
    queryset = ConnLog.objects.all().order_by('-conn_start')
    
    # 필터링
    if user_pkid or username:
        # 사용자의 등록된 기기 목록에서 remote_id 가져오기
        from api.models import MdeskDeviceRegistration
        
        device_filter = Q()
        if user_pkid:
            device_filter |= Q(user_pkid=user_pkid)
        if username:
            device_filter |= Q(custom_id=username)
        
        # 해당 사용자의 등록된 기기들의 remote_id 목록
        device_ids = list(MdeskDeviceRegistration.objects.filter(device_filter).values_list('remote_id', flat=True))
        
        if device_ids:
            # from_id 또는 rid가 사용자의 기기 목록에 있는 세션만 조회
            queryset = queryset.filter(Q(from_id__in=device_ids) | Q(rid__in=device_ids))
        else:
            # 등록된 기기가 없으면 빈 결과
            queryset = queryset.none()
    elif client_id:
        # 클라이언트 ID로 직접 필터링
        queryset = queryset.filter(Q(from_id__icontains=client_id) | Q(rid__icontains=client_id))
    
    # 중복 제거를 위해 더 많이 가져온 후 처리
    sessions = queryset[:limit * 5]  # 중복 제거 후 limit 개수를 맞추기 위해 여유있게 가져옴
    
    # 기기 정보 조회를 위한 캐시
    from api.models import MdeskDeviceRegistration
    device_info_cache = {}
    
    def get_device_info(device_id):
        """기기 ID로 alias, hostname 조회"""
        if device_id in device_info_cache:
            return device_info_cache[device_id]
        
        # MdeskDeviceRegistration에서 조회
        device = MdeskDeviceRegistration.objects.filter(remote_id=device_id).first()
        if device:
            info = {
                'alias': device.alias or '',
                'hostname': device.hostname or ''
            }
        else:
            # RustDeskPeer에서 조회
            peer = RustDeskPeer.objects.filter(rid=device_id).first()
            if peer:
                info = {
                    'alias': peer.alias or '',
                    'hostname': peer.hostname or ''
                }
            else:
                info = {'alias': '', 'hostname': ''}
        
        device_info_cache[device_id] = info
        return info
    
    data = []
    seen_to_ids = set()  # 중복 체크용 (to_id 기준)
    
    for session in sessions:
        # 중복 체크: to_id가 이미 있으면 스킵 (최근 접속만 표시)
        to_id = session.rid or ''
        if to_id in seen_to_ids:
            continue
        seen_to_ids.add(to_id)
        
        # limit 개수에 도달하면 종료
        if len(data) >= limit:
            break
        
        # 연결 시간 계산
        duration = ''
        if session.conn_start and session.conn_end:
            delta = session.conn_end - session.conn_start
            total_seconds = int(delta.total_seconds())
            if total_seconds < 60:
                duration = f'{total_seconds}초'
            elif total_seconds < 3600:
                duration = f'{total_seconds // 60}분 {total_seconds % 60}초'
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                duration = f'{hours}시간 {minutes}분'
        elif session.conn_start and not session.conn_end:
            duration = '연결 중'
        
        # 기기 정보 조회 (to_id만)
        to_info = get_device_info(session.rid) if session.rid else {'alias': '', 'hostname': ''}
        
        data.append({
            'id': session.rid or '',
            'alias': to_info['alias'],
            'hostname': to_info['hostname'],
            'conn_start': session.conn_start.strftime('%Y-%m-%d %H:%M:%S') if session.conn_start else '',
            'conn_end': session.conn_end.strftime('%Y-%m-%d %H:%M:%S') if session.conn_end else '',
            'duration': duration,
            'session_id': session.session_id or '',
        })
    
    return JsonResponse({
        'code': 1,
        'count': len(data),
        'data': data
    })


def audit_file(request):
    """파일 전송 기록 API - /api/audit/file"""
    if request.method == 'GET' or not request.body:
        return JsonResponse({'code': 1, 'data': 'ok'})
    
    try:
        postdata = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 1, 'data': 'ok'})
    
    print('audit_file:', postdata)
    
    try:
        info = json.loads(postdata.get('info', '{}'))
        files = info.get('files', [])
        filesize = convert_filesize(int(files[0][1])) if files else '0B'
        
        new_file_log = FileLog(
            file=postdata.get('path', ''),
            user_id=postdata.get('peer_id', ''),
            user_ip=info.get('ip', ''),
            remote_id=postdata.get('id', ''),
            filesize=filesize,
            direction=postdata.get('type', ''),
            logged_at=datetime.datetime.now(),
        )
        new_file_log.save()
    except Exception as e:
        print('audit_file error:', e)
    
    return JsonResponse({'code': 1, 'data': 'ok'})


def audit_alarm(request):
    """경고 기록 API - /api/audit/alarm (IP 차단 등)"""
    if request.method == 'GET' or not request.body:
        return JsonResponse({'code': 1, 'data': 'ok'})
    
    try:
        postdata = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 1, 'data': 'ok'})
    
    print('audit_alarm:', postdata)
    
    # 경고 로그 처리 (필요 시 별도 테이블에 저장 가능)
    # 현재는 로그만 출력
    
    return JsonResponse({'code': 1, 'data': 'ok'})


def convert_filesize(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def users(request):
    result = {
        'code': 1,
        'data': _('확인')
    }
    return JsonResponse(result)


def peers(request):
    result = {
        'code': 1,
        'data': 'ok'
    }
    return JsonResponse(result)


def device_groups(request):
    """
    RustDesk 클라이언트의 device groups API 요청 처리
    빈 그룹 목록 반환
    """
    result = {
        'code': 1,
        'data': []
    }
    return JsonResponse(result)


def device_group_accessible(request):
    """
    RustDesk 클라이언트의 device-group/accessible API 요청 처리
    """
    result = {
        'total': 2,
        'data': [
            {'name': '그룹1'},
            {'name': '그룹2'}
        ]
    }
    return JsonResponse(result)


def group(request):
    """
    RustDesk 클라이언트의 group API 요청 처리
    빈 그룹 목록 반환
    """
    result = {
        'code': 1,
        'data': {
            'groups': [],
            'users': []
        }
    }
    return JsonResponse(result)


def add_support_agent(request, username):
    """
    상담원 추가 API
    URL: /api/<username>/addnum
    보안: Bearer Token 인증 (로컬 테스트 시 토큰 없이 가능)
    """
    from django.conf import settings
    
    result = {}
    
    # [디버그] 요청 정보 출력
    print(f"\n[ADD_AGENT_DEBUG] 요청된 username: {username}")
    
    # 클라이언트 IP 확인
    client_ip = get_client_ip(request)
    is_local = client_ip in ['127.0.0.1', 'localhost', '::1']
    is_debug = getattr(settings, 'DEBUG', False)
    
    print(f"[ADD_AGENT_DEBUG] 클라이언트 IP: {client_ip}, 로컬: {is_local}, DEBUG: {is_debug}")
    
    # 로컬 테스트 모드: DEBUG=True이고 로컬 IP인 경우 토큰 인증 건너뛰기
    if is_debug and is_local:
        print("[ADD_AGENT_DEBUG] 로컬 테스트 모드 - 토큰 인증 건너뜀")
        token_user = UserProfile.objects.filter(username=username).first()
        if not token_user:
            print(f"[ADD_AGENT_DEBUG] 에러: 사용자 '{username}'를 찾을 수 없음")
            return JsonResponse({'error': _('사용자를 찾을 수 없습니다.')}, status=404)
    else:
        # 1. 토큰 확인
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        print(f"[ADD_AGENT_DEBUG] Authorization Header: {auth_header}")
        
        if not auth_header.startswith('Bearer '):
            print("[ADD_AGENT_DEBUG] 에러: Bearer 토큰 형식이 아님")
            return JsonResponse({'error': _('인증 토큰이 없습니다.')}, status=401)
        
        access_token = auth_header.split(' ')[1]
        print(f"[ADD_AGENT_DEBUG] 추출된 토큰: {access_token}")
        
        token_obj = RustDeskToken.objects.filter(access_token=access_token).first()
        
        if not token_obj:
            print("[ADD_AGENT_DEBUG] 에러: DB에서 토큰을 찾을 수 없음")
            return JsonResponse({'error': _('유효하지 않은 토큰입니다.')}, status=401)
        
        print(f"[ADD_AGENT_DEBUG] 토큰 소유자(DB): {token_obj.username}")
        
        # 2. 권한 확인 (토큰 주인과 요청받은 username이 일치하는지)
        token_user = UserProfile.objects.filter(username=token_obj.username).first()
        if not token_user or token_user.username != username:
            print(f"[ADD_AGENT_DEBUG] 에러: 권한 불일치 (토큰주인:{token_obj.username} != 요청아이디:{username})")
            return JsonResponse({'error': _('권한이 없습니다.')}, status=403)
    
    print("[ADD_AGENT_DEBUG] 인증 및 권한 확인 성공")
    
    # 3. 상담원 추가 로직
    # 오늘 날짜와 캐시 키 설정
    now = datetime.datetime.now()
    today_str = now.strftime('%Y%m%d')
    cache_key = f"last_agent_num_{username}_{today_str}"
    
    # 1. 캐시에서 오늘 마지막으로 사용한 번호 가져오기
    current_last_num = cache.get(cache_key)
    
    if current_last_num is None:
        # 2. 캐시에 없으면 DB에서 오늘 생성된 가장 큰 번호 찾기 (서버 재시작 등 대비)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 현재 존재하는 상담원 중 최대 번호
        last_agent = SupportAgent.objects.filter(
            uid=token_user, 
            create_time__gte=today_start
        ).order_by('-agent_num').first()
        max_from_agents = last_agent.agent_num if last_agent else 0
        
        # 오늘 접속 기록 중 최대 상담원 번호 (삭제된 상담원 포함)
        last_connection = AgentConnectionLog.objects.filter(
            uid=token_user,
            create_time__gte=today_start
        ).order_by('-agent_num').first()
        max_from_logs = last_connection.agent_num if last_connection else 0
        
        # 둘 중 큰 값 사용 (삭제된 상담원까지 고려)
        current_last_num = max(max_from_agents, max_from_logs)
        print(f"[ADD_AGENT_DEBUG] DB 조회 결과 - 현재상담원:{max_from_agents}, 접속기록:{max_from_logs}, 최종:{current_last_num}")
    
    # 다음 번호 부여
    next_num = current_last_num + 1
    
    # 3. 새로운 마지막 번호를 캐시에 저장 (오늘 하루 유지)
    cache.set(cache_key, next_num, 86400)
    
    # 새 상담원 생성
    new_agent = SupportAgent.objects.create(
        uid=token_user,
        agent_num=next_num,
        agent_name=f'상담원 {next_num}'
    )
    
    print(f"[ADD_AGENT_DEBUG] 상담원 추가 완료: {new_agent.agent_name}")
    
    return JsonResponse({
        'code': 1,
        'msg': _('상담원이 성공적으로 추가되었습니다.'),
        'data': {
            'agent_num': new_agent.agent_num,
            'agent_name': new_agent.agent_name
        }
    })


def get_support_agents(request, username):
    """
    상담원 목록 조회 API
    URL: /api/<username>/agents
    보안: Bearer Token 인증
    """
    # 1. 토큰 확인
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({'error': _('인증 토큰이 없습니다.')}, status=401)
    
    access_token = auth_header.split(' ')[1]
    token_obj = RustDeskToken.objects.filter(access_token=access_token).first()
    
    if not token_obj:
        return JsonResponse({'error': _('유효하지 않은 토큰입니다.')}, status=401)
    
    # 2. 권한 확인
    token_user = UserProfile.objects.filter(username=token_obj.username).first()
    if not token_user or token_user.username != username:
        return JsonResponse({'error': _('권한이 없습니다.')}, status=403)
    
    # 3. 상담원 목록 조회
    agents = SupportAgent.objects.filter(uid=token_user).order_by('agent_num')
    data = []
    now = datetime.datetime.now()
    ten_minutes_ago = now - datetime.timedelta(minutes=10)
    
    # 등록된 상담원 번호 집합
    registered_agent_nums = set()
    
    for agent in agents:
        registered_agent_nums.add(agent.agent_num)
        # 해당 상담원 번호로 최근 접속한 mdesk_id 조회 (10분 이내만)
        latest_connection = AgentConnectionLog.objects.filter(
            uid=token_user,
            agent_num=agent.agent_num,
            create_time__gte=ten_minutes_ago
        ).order_by('-create_time').first()
        
        agent_data = {
            'agent_num': agent.agent_num,
            'agent_name': agent.agent_name,
            'create_time': agent.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'mdesk_id': latest_connection.mdesk_id if latest_connection else ''
        }
        data.append(agent_data)
    
    # 4. agent_num = 0인 접속 기록 확인 (SupportAgent에 없어도 표시)
    if 0 not in registered_agent_nums:
        zero_connection = AgentConnectionLog.objects.filter(
            uid=token_user,
            agent_num=0,
            create_time__gte=ten_minutes_ago
        ).order_by('-create_time').first()
        
        if zero_connection:
            # agent_num = 0인 접속 기록이 있으면 목록에 추가
            agent_data = {
                'agent_num': 0,
                'agent_name': '기본 상담원',
                'create_time': zero_connection.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'mdesk_id': zero_connection.mdesk_id
            }
            # 맨 앞에 추가
            data.insert(0, agent_data)
    
    return JsonResponse({
        'code': 1,
        'data': data
    })


def delete_support_agent(request, username, agent_num):
    """
    상담원 삭제 API
    URL: /api/<username>/delnum/<agent_num>
    보안: Bearer Token 인증
    """
    # 1. 토큰 확인
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({'error': _('인증 토큰이 없습니다.')}, status=401)
    
    access_token = auth_header.split(' ')[1]
    token_obj = RustDeskToken.objects.filter(access_token=access_token).first()
    
    if not token_obj:
        return JsonResponse({'error': _('유효하지 않은 토큰입니다.')}, status=401)
    
    # 2. 권한 확인
    token_user = UserProfile.objects.filter(username=token_obj.username).first()
    if not token_user or token_user.username != username:
        return JsonResponse({'error': _('권한이 없습니다.')}, status=403)
    
    # 3. 상담원 삭제
    agent = SupportAgent.objects.filter(uid=token_user, agent_num=agent_num).first()
    if not agent:
        return JsonResponse({'error': _('해당 상담원을 찾을 수 없습니다.')}, status=404)
    
    agent.delete()
    
    return JsonResponse({
        'code': 1,
        'msg': _('상담원이 성공적으로 삭제되었습니다.')
    })


def get_public_agent_status(request, username):
    """
    공개 상담원 상태 조회 API (상담원 페이지 자동 리프레시용)
    URL: /api/<username>/public_agents
    """
    user = UserProfile.objects.filter(username=username).first()
    if not user:
        return JsonResponse({'code': 0, 'msg': 'User not found'})

    agents = SupportAgent.objects.filter(uid=user).order_by('agent_num')
    agent_list = [agent.agent_num for agent in agents]

    return JsonResponse({
        'code': 1,
        'agent_list': agent_list
    })


def update_agent_connection(request, userid, mdeskid):
    """
    상담원 접속 정보 업데이트 API
    URL: /agentnumupdate/<userid>/<mdeskid>?agentid=11
    """
    import re
    # (2), (3) 등 브라우저 중복 다운로드 접미사 제거 로직 추가
    def clean_param(val):
        if not val: return val
        return re.sub(r'\s\(\d+\)$', '', str(val)).strip()

    userid = clean_param(userid)
    mdeskid = clean_param(mdeskid)
    agent_id = clean_param(request.GET.get('agentid'))
    
    # [로그] 요청 정보 출력
    print(f"\n[AGENT_UPDATE_LOG] 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[AGENT_UPDATE_LOG] UserID: {userid}, MDeskID: {mdeskid}, AgentID: {agent_id}")
    
    if not agent_id:
        print("[AGENT_UPDATE_LOG] 결과: 실패 (agentid 파라미터 없음)")
        return JsonResponse({'error': 'agentid parameter is required'}, status=400)
    
    try:
        agent_num = int(agent_id)
    except ValueError:
        print(f"[AGENT_UPDATE_LOG] 결과: 실패 (유효하지 않은 agentid: {agent_id})")
        return JsonResponse({'error': 'agentid must be an integer'}, status=400)
    
    user = UserProfile.objects.filter(username=userid).first()
    if not user:
        print(f"[AGENT_UPDATE_LOG] 결과: 실패 (사용자 찾을 수 없음: {userid})")
        return JsonResponse({'error': 'User not found'}, status=404)
    
    # 오늘 날짜 구하기
    now = datetime.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 같은 mdesk_id로 오늘 생성된 다른 상담원 번호의 기록들을 모두 삭제 (초기화)
    deleted_count = AgentConnectionLog.objects.filter(
        uid=user,
        mdesk_id=mdeskid,
        create_time__gte=today_start
    ).exclude(agent_num=agent_num).delete()[0]
    
    if deleted_count > 0:
        print(f"[AGENT_UPDATE_LOG] 기존 상담원 번호 기록 {deleted_count}개 삭제됨")
    
    # 오늘 이미 등록된 동일한 상담원 번호가 있는지 확인 (중복 방지)
    exists = AgentConnectionLog.objects.filter(
        uid=user,
        mdesk_id=mdeskid,
        agent_num=agent_num,
        create_time__gte=today_start
    ).exists()
    
    if not exists:
        AgentConnectionLog.objects.create(
            uid=user,
            mdesk_id=mdeskid,
            agent_num=agent_num
        )
        msg = "Registered successfully"
        print(f"[AGENT_UPDATE_LOG] 결과: 성공 (신규 기록 저장 완료, 기존 기록 {deleted_count}개 삭제)")
    else:
        msg = "Already registered for today"
        print(f"[AGENT_UPDATE_LOG] 결과: 중복 (오늘 이미 기록된 상담원 번호, 기존 다른 기록 {deleted_count}개 삭제)")
        
    return JsonResponse({
        'code': 1,
        'msg': msg,
        'data': {
            'userid': userid,
            'mdeskid': mdeskid,
            'agentid': agent_num
        }
    })


def agent_close(request, userid, agentid):
    """
    RustDesk 클라이언트 종료 시 상담원 삭제 API
    URL: /api/agentclose/<userid>/<agentid>
    
    - 해당 상담원(SupportAgent) 삭제
    - 관련 접속 기록(AgentConnectionLog) 삭제
    """
    import re
    # (2), (3) 등 브라우저 중복 다운로드 접미사 제거
    def clean_param(val):
        if not val: return val
        return re.sub(r'\s\(\d+\)$', '', str(val)).strip()

    userid = clean_param(userid)
    agentid = clean_param(agentid)
    
    print(f"\n[AGENT_CLOSE_LOG] 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[AGENT_CLOSE_LOG] UserID: {userid}, AgentID: {agentid}")
    
    try:
        agent_num = int(agentid)
    except ValueError:
        print(f"[AGENT_CLOSE_LOG] 결과: 실패 (유효하지 않은 agentid: {agentid})")
        return JsonResponse({'error': 'agentid must be an integer'}, status=400)
    
    user = UserProfile.objects.filter(username=userid).first()
    if not user:
        print(f"[AGENT_CLOSE_LOG] 결과: 실패 (사용자 찾을 수 없음: {userid})")
        return JsonResponse({'error': 'User not found'}, status=404)
    
    # 1. 상담원(SupportAgent) 삭제
    agent = SupportAgent.objects.filter(uid=user, agent_num=agent_num).first()
    agent_deleted = False
    if agent:
        agent.delete()
        agent_deleted = True
        print(f"[AGENT_CLOSE_LOG] 상담원 삭제됨: 상담원 {agent_num}")
    else:
        print(f"[AGENT_CLOSE_LOG] 상담원 없음: 상담원 {agent_num}")
    
    # 2. 오늘 접속 기록(AgentConnectionLog) 삭제
    now = datetime.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    deleted_logs = AgentConnectionLog.objects.filter(
        uid=user,
        agent_num=agent_num,
        create_time__gte=today_start
    ).delete()[0]
    
    print(f"[AGENT_CLOSE_LOG] 접속 기록 {deleted_logs}개 삭제됨")
    
    # 3. MdeskDeviceRegistration 테이블에서 agent_id 초기화
    updated_devices = MdeskDeviceRegistration.objects.filter(
        agent_id=str(agent_num)
    ).update(agent_id='')
    
    print(f"[AGENT_CLOSE_LOG] MdeskDeviceRegistration agent_id 초기화: {updated_devices}개")
    print(f"[AGENT_CLOSE_LOG] 결과: 성공")
    
    return JsonResponse({
        'code': 1,
        'msg': 'Agent closed successfully',
        'data': {
            'userid': userid,
            'agentid': agent_num,
            'agent_deleted': agent_deleted,
            'logs_deleted': deleted_logs,
            'devices_updated': updated_devices
        }
    })


def custom_app_config(request):
    """
    커스텀 앱 설정 정보 조회 API
    RustDesk 클라이언트에서 사용자의 커스텀 앱 설정을 가져올 수 있습니다.
    
    인증: username (로그인 아이디) 사용
    """
    result = {}
    
    if request.method == 'GET':
        result['error'] = _('잘못된 제출 방식! POST 방식을 사용하세요.')
        return JsonResponse(result)
    
    # POST body에서 username 받기
    try:
        data = json.loads(request.body.decode())
        username = data.get('username', '') or data.get('user', '')
    except:
        username = ''
    
    # username 필수
    if not username:
        result['error'] = _('username이 필요합니다!')
        return JsonResponse(result)
    
    # username (로그인 아이디)로 사용자 찾기
    user = UserProfile.objects.filter(Q(username=username)).first()
    
    if not user:
        result['error'] = _('해당 사용자를 찾을 수 없습니다! (username 확인 필요)')
        return JsonResponse(result)
    
    # 커스텀 앱 설정 가져오기
    custom_config = CustomAppConfig.objects.filter(uid=user).first()
    
    # 릴레이 서버 퍼블릭 키 조회
    relay_pub_key = ''
    if user.relay_server:
        rs = RelayServer.objects.filter(server_address=user.relay_server).first()
        if rs:
            relay_pub_key = rs.public_key

    if not custom_config:
        # 기본값 반환
        result['code'] = 1
        result['data'] = {
            'app_name': 'MDesk',
            'logo_url': '',
            'password': '',
            'encrypted_password': '',
            'title': 'Your Desktop',
            'description': 'Your desktop can be accessed with this ID and password.',
            'relay_server': user.relay_server,
            'relay_pub_key': relay_pub_key
        }
        return JsonResponse(result)
    
    # 암호화된 암호 계산
    from .views_front import encrypt_password
    encrypted_password = encrypt_password(custom_config.password) if custom_config.password else ''
    
    # 로고 URL 생성
    logo_url = ''
    if custom_config.logo:
        try:
            logo_url = custom_config.logo.url
            # 절대 URL로 변환
            if request:
                logo_url = request.build_absolute_uri(logo_url)
        except:
            logo_url = ''
    
    # 결과 반환
    result['code'] = 1
    result['data'] = {
        'app_name': custom_config.app_name,
        'logo_url': logo_url,
        'password': custom_config.password,  # 원본 암호 (필요시)
        'encrypted_password': encrypted_password,  # 암호화된 암호
        'title': custom_config.title,
        'description': custom_config.description,
        'relay_server': user.relay_server,
        'relay_pub_key': relay_pub_key,
        'created_at': custom_config.create_time.strftime('%Y-%m-%d %H:%M:%S') if custom_config.create_time else '',
        'updated_at': custom_config.update_time.strftime('%Y-%m-%d %H:%M:%S') if custom_config.update_time else ''
    }
    
    return JsonResponse(result)


def app_version(request):
    """
    MDesk 실행파일 버전 정보 조회 API
    
    GET /api/app_version
    
    반환:
    - file_version: 파일 버전 (예: 1.0.0.0)
    - product_version: 제품 버전
    - product_name: 제품명
    - file_description: 파일 설명
    - company_name: 회사명
    - file_size: 파일 크기 (바이트)
    - file_name: 파일명
    """
    result = {
        'code': 0,
        'msg': '',
        'data': {}
    }
    
    # 실행파일 경로 확인
    executable_dir = getattr(settings, 'EXECUTABLE_DIR', os.path.join(settings.BASE_DIR, 'executables'))
    
    # 가능한 파일명들
    possible_names = [
        'MDesk_portable.exe',
        'MDesk_portable-id=admin.exe',
        'MDesk.exe',
        'rustdesk_portable.exe'
    ]
    
    exe_path = None
    exe_name = None
    for name in possible_names:
        path = os.path.join(executable_dir, name)
        if os.path.exists(path):
            exe_path = path
            exe_name = name
            break
    
    if not exe_path:
        result['msg'] = _('실행파일을 찾을 수 없습니다.')
        result['data'] = {
            'searched_path': executable_dir,
            'searched_files': possible_names
        }
        return JsonResponse(result)
    
    try:
        import pefile
        
        pe = pefile.PE(exe_path)
        
        version_info = {}
        
        # 버전 정보 추출
        if hasattr(pe, 'VS_VERSIONINFO'):
            for fileinfo in pe.FileInfo:
                for entry in fileinfo:
                    if hasattr(entry, 'StringTable'):
                        for st in entry.StringTable:
                            for key, value in st.entries.items():
                                # 바이트 문자열을 일반 문자열로 변환
                                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                                value_str = value.decode('utf-8') if isinstance(value, bytes) else value
                                version_info[key_str] = value_str
                    
                    if hasattr(entry, 'FixedFileInfo'):
                        # 파일 버전 추출 (숫자 형식)
                        ms = entry.FixedFileInfo.FileVersionMS
                        ls = entry.FixedFileInfo.FileVersionLS
                        version_info['FileVersionNumeric'] = f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
                        
                        # 제품 버전 추출 (숫자 형식)
                        ms = entry.FixedFileInfo.ProductVersionMS
                        ls = entry.FixedFileInfo.ProductVersionLS
                        version_info['ProductVersionNumeric'] = f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
        
        pe.close()
        
        # 파일 크기
        file_size = os.path.getsize(exe_path)
        
        result['code'] = 1
        result['msg'] = _('버전 정보 조회 성공')
        result['data'] = {
            'file_name': exe_name,
            'file_path': exe_path,
            'file_size': file_size,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'file_version': version_info.get('FileVersion', version_info.get('FileVersionNumeric', '')),
            'product_version': version_info.get('ProductVersion', version_info.get('ProductVersionNumeric', '')),
            'product_name': version_info.get('ProductName', ''),
            'file_description': version_info.get('FileDescription', ''),
            'company_name': version_info.get('CompanyName', ''),
            'original_filename': version_info.get('OriginalFilename', ''),
            'internal_name': version_info.get('InternalName', ''),
            'legal_copyright': version_info.get('LegalCopyright', ''),
            'all_info': version_info
        }
        
    except ImportError:
        result['msg'] = _('pefile 라이브러리가 설치되지 않았습니다. pip install pefile')
    except Exception as e:
        result['msg'] = _('버전 정보 추출 중 오류: {}').format(str(e))
    
    return JsonResponse(result)


def upload_executable(request):
    """
    실행파일 업로드 API
    
    POST /api/version/upload
    
    필수 파라미터:
    - api_key: 업로드 인증 키 (환경변수 UPLOAD_API_KEY와 일치해야 함)
    - file: 업로드할 파일 (.exe)
    
    선택 파라미터:
    - filename: 저장할 파일명 (없으면 원본 파일명 사용)
    """
    result = {
        'code': 0,
        'msg': ''
    }
    
    if request.method != 'POST':
        result['msg'] = _('POST 요청만 허용됩니다.')
        return JsonResponse(result, status=405)
    
    # API 키 확인
    api_key = request.POST.get('api_key', '')
    expected_key = os.environ.get('UPLOAD_API_KEY', '')
    
    if not expected_key:
        result['msg'] = _('서버에 UPLOAD_API_KEY가 설정되지 않았습니다.')
        return JsonResponse(result, status=500)
    
    if api_key != expected_key:
        result['msg'] = _('API 키가 올바르지 않습니다.')
        return JsonResponse(result, status=403)
    
    # 파일 확인
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        result['msg'] = _('파일이 업로드되지 않았습니다.')
        return JsonResponse(result, status=400)
    
    # 파일 확장자 확인
    original_name = uploaded_file.name
    if not original_name.lower().endswith('.exe'):
        result['msg'] = _('.exe 파일만 업로드 가능합니다.')
        return JsonResponse(result, status=400)
    
    # 저장할 파일명 결정
    save_filename = request.POST.get('filename', '').strip()
    if not save_filename:
        save_filename = original_name
    
    # .exe 확장자 보장
    if not save_filename.lower().endswith('.exe'):
        save_filename += '.exe'
    
    # 파일명 보안 검사 (경로 탐색 공격 방지)
    if '/' in save_filename or '\\' in save_filename or '..' in save_filename:
        result['msg'] = _('잘못된 파일명입니다.')
        return JsonResponse(result, status=400)
    
    # 저장 경로
    executable_dir = getattr(settings, 'EXECUTABLE_DIR', os.path.join(settings.BASE_DIR, 'executables'))
    os.makedirs(executable_dir, exist_ok=True)
    
    save_path = os.path.join(executable_dir, save_filename)
    
    # 기존 파일 백업 (있는 경우)
    backup_path = None
    if os.path.exists(save_path):
        backup_filename = f"{save_filename}.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        backup_path = os.path.join(executable_dir, backup_filename)
        try:
            os.rename(save_path, backup_path)
        except Exception as e:
            result['msg'] = _('기존 파일 백업 실패: {}').format(str(e))
            return JsonResponse(result, status=500)
    
    # 파일 저장
    try:
        with open(save_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        file_size = os.path.getsize(save_path)
        
        result['code'] = 1
        result['msg'] = _('파일이 성공적으로 업로드되었습니다.')
        result['data'] = {
            'filename': save_filename,
            'original_name': original_name,
            'file_size': file_size,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'backup_file': backup_path.split(os.sep)[-1] if backup_path else None,
            'upload_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print(f"[업로드 성공] {save_filename} ({file_size} bytes)")
        
    except Exception as e:
        # 업로드 실패 시 백업 복원
        if backup_path and os.path.exists(backup_path):
            try:
                os.rename(backup_path, save_path)
            except:
                pass
        
        result['msg'] = _('파일 저장 중 오류: {}').format(str(e))
        return JsonResponse(result, status=500)
    
    return JsonResponse(result)


def verify_remote_user(request):
    """원격 사용자 인증 API
    
    요청: POST /api/verify_remote_user
    {
        "username": "아이디",
        "password": "암호",
        "remote_id": "원격지 ID (선택)",
        "remote_hostname": "원격지 호스트명 (선택)",
        "memo": "메모 (선택)"
    }
    
    응답 (성공):
    {
        "code": 1,
        "data": {
            "username": "아이디",
            "name": "사용자 이름"
        }
    }
    
    응답 (실패):
    {
        "code": 0,
        "message": "아이디 또는 암호가 올바르지 않습니다"
    }
    """
    result = {}
    
    # 클라이언트 정보 수집
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    if request.method != 'POST':
        result['code'] = 0
        result['message'] = _('POST 방식으로 요청하세요.')
        return JsonResponse(result)
    
    try:
        data = json.loads(request.body.decode())
    except:
        result['code'] = 0
        result['message'] = _('잘못된 요청 형식입니다.')
        return JsonResponse(result)
    
    username = data.get('username', '')
    password = data.get('password', '')
    remote_id = data.get('remote_id', '')
    remote_hostname = data.get('remote_hostname', '')
    memo = data.get('memo', '')
    
    if not username or not password:
        result['code'] = 0
        result['message'] = _('아이디 또는 암호가 올바르지 않습니다')
        return JsonResponse(result)
    
    # 사용자 인증
    user = auth.authenticate(username=username, password=password)
    
    if not user:
        # 인증 실패 로그 저장
        RemoteAuthLog.objects.create(
            user=None,
            username=username,
            remote_id=remote_id,
            remote_hostname=remote_hostname,
            client_ip=client_ip,
            user_agent=user_agent,
            success=False,
            memo=memo
        )
        result['code'] = 0
        result['message'] = _('아이디 또는 암호가 올바르지 않습니다')
        return JsonResponse(result)
    
    # 비활성화된 사용자 체크
    if not user.is_active:
        # 비활성화 사용자 로그 저장
        RemoteAuthLog.objects.create(
            user=user,
            username=username,
            remote_id=remote_id,
            remote_hostname=remote_hostname,
            client_ip=client_ip,
            user_agent=user_agent,
            success=False,
            memo=f"{memo} (비활성화 계정)" if memo else "비활성화 계정"
        )
        result['code'] = 0
        result['message'] = _('아이디 또는 암호가 올바르지 않습니다')
        return JsonResponse(result)
    
    # 인증 성공 로그 저장
    RemoteAuthLog.objects.create(
        user=user,
        username=username,
        remote_id=remote_id,
        remote_hostname=remote_hostname,
        client_ip=client_ip,
        user_agent=user_agent,
        success=True,
        memo=memo
    )
    
    # 인증 성공
    result['code'] = 1
    result['data'] = {
        'username': user.username,
        'name': user.company_name if user.company_name else user.username
    }
    
    return JsonResponse(result)


@csrf_exempt
def device_register(request):
    """MDesk 기기 등록 API
    
    엔드포인트: POST /api/device/register
    Content-Type: application/json
    인증: Authorization: Bearer {access_token} (선택사항)
    
    요청 데이터:
    {
        "user_id": "imedix",                    // 로그인된 유저 ID (username)
        "user_pkid": "3",                       // 유저 고유 번호
        "remote_id": "143165320",               // 원격 ID (peer ID)
        "alias": "사무실개발컴",                 // 사용자 지정 별칭
        "hostname": "DESKTOP-ABC123",           // 실제 컴퓨터 이름
        "platform": "Windows",                  // OS 플랫폼
        "uuid": "xxxxxxxx-xxxx-xxxx",           // 장치 고유 UUID
        "version": "1.3.6",                     // RustDesk 버전
        "agent_id": "4"                         // 상담원 번호 (선택)
    }
    
    응답 (성공 - 200 OK):
    {
        "success": true,
        "message": "Device registered successfully",
        "data": {
            "device_id": 12345,
            "remote_id": "143165320",
            "alias": "사무실개발컴",
            "registered_at": "2026-01-13T12:00:00Z"
        }
    }
    
    응답 (실패 - 400/401/500):
    {
        "success": false,
        "error": "ERROR_CODE",
        "message": "에러 메시지"
    }
    """
    result = {}
    
    if request.method != 'POST':
        result['success'] = False
        result['error'] = 'METHOD_NOT_ALLOWED'
        result['message'] = _('POST 방식으로 요청하세요.')
        return JsonResponse(result, status=405)
    
    # 클라이언트 정보 수집
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    try:
        data = json.loads(request.body.decode())
    except:
        result['success'] = False
        result['error'] = 'INVALID_JSON'
        result['message'] = _('잘못된 요청 형식입니다.')
        return JsonResponse(result, status=400)
    
    # 요청 데이터 추출 (새 형식 우선, 구 형식 호환)
    remote_id = data.get('remote_id', '')
    user_id = data.get('user_id', '') or data.get('custom_id', '')  # user_id 또는 custom_id
    user_pkid = data.get('user_pkid', '')
    agent_id = data.get('agent_id', '')
    alias = data.get('alias', '')
    hostname = data.get('hostname', '')
    platform = data.get('platform', '')
    uuid = data.get('uuid', '')
    version = data.get('version', '')
    
    # 필수 필드 확인
    if not remote_id:
        result['success'] = False
        result['error'] = 'MISSING_REMOTE_ID'
        result['message'] = _('remote_id는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    try:
        # 기존 등록 정보 확인 (동일한 remote_id + user_id 조합)
        existing_device = MdeskDeviceRegistration.objects.filter(
            remote_id=remote_id,
            custom_id=user_id
        ).first()
        
        if existing_device:
            # 기존 기기 정보 업데이트
            existing_device.user_pkid = user_pkid or existing_device.user_pkid
            existing_device.agent_id = agent_id or existing_device.agent_id
            existing_device.alias = alias or existing_device.alias
            existing_device.hostname = hostname or existing_device.hostname
            existing_device.platform = platform or existing_device.platform
            existing_device.uuid = uuid or existing_device.uuid
            existing_device.version = version or existing_device.version
            existing_device.client_ip = client_ip
            existing_device.user_agent = user_agent
            existing_device.is_active = True
            existing_device.save()
            device = existing_device
            created = False
        else:
            # 새 기기 등록
            device = MdeskDeviceRegistration.objects.create(
                remote_id=remote_id,
                custom_id=user_id,
                user_pkid=user_pkid,
                agent_id=agent_id,
                alias=alias,
                hostname=hostname,
                platform=platform,
                uuid=uuid,
                version=version,
                client_ip=client_ip,
                user_agent=user_agent,
                is_active=True
            )
            created = True
        
        result['success'] = True
        result['message'] = _('Device registered successfully') if created else _('Device updated successfully')
        result['data'] = {
            'device_id': device.id,
            'remote_id': device.remote_id,
            'alias': device.alias,
            'hostname': device.hostname,
            'platform': device.platform,
            'registered_at': device.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'updated_at': device.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        print(f"[DEVICE_REGISTER] {'신규 등록' if created else '정보 업데이트'}: {remote_id} ({user_id}/{agent_id}) from {client_ip}")
        return JsonResponse(result, status=200)
        
    except Exception as e:
        result['success'] = False
        result['error'] = 'INTERNAL_ERROR'
        result['message'] = _('기기 등록 중 오류가 발생했습니다: {}').format(str(e))
        print(f"[DEVICE_REGISTER] 오류: {str(e)}")
        return JsonResponse(result, status=500)


@csrf_exempt
def device_unregister(request):
    """MDesk 기기 등록 해제 API
    
    엔드포인트: POST /api/device/unregister
    Content-Type: application/json
    
    요청 데이터:
    {
        "user_id": "imedix",           // 사용자 ID (username)
        "remote_id": "527085412"       // 원격 ID (peer ID)
    }
    
    응답 (성공 - 200 OK):
    {
        "success": true,
        "message": "Device unregistered successfully",
        "data": {
            "user_id": "imedix",
            "remote_id": "527085412"
        }
    }
    
    응답 (실패 - 400/404/500):
    {
        "success": false,
        "error": "ERROR_CODE",
        "message": "에러 메시지"
    }
    """
    result = {}
    
    if request.method != 'POST':
        result['success'] = False
        result['error'] = 'METHOD_NOT_ALLOWED'
        result['message'] = _('POST 방식으로 요청하세요.')
        return JsonResponse(result, status=405)
    
    # 클라이언트 정보 수집
    client_ip = get_client_ip(request)
    
    try:
        data = json.loads(request.body.decode())
    except:
        result['success'] = False
        result['error'] = 'INVALID_JSON'
        result['message'] = _('잘못된 요청 형식입니다.')
        return JsonResponse(result, status=400)
    
    # 요청 데이터 추출
    user_id = data.get('user_id', '')
    remote_id = data.get('remote_id', '')
    
    # 필수 필드 확인
    if not user_id:
        result['success'] = False
        result['error'] = 'MISSING_USER_ID'
        result['message'] = _('user_id는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    if not remote_id:
        result['success'] = False
        result['error'] = 'MISSING_REMOTE_ID'
        result['message'] = _('remote_id는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    try:
        # 해당 기기 조회
        device = MdeskDeviceRegistration.objects.filter(
            remote_id=remote_id,
            custom_id=user_id
        ).first()
        
        if not device:
            result['success'] = False
            result['error'] = 'DEVICE_NOT_FOUND'
            result['message'] = _('등록된 기기를 찾을 수 없습니다.')
            return JsonResponse(result, status=404)
        
        # 기기 삭제
        device.delete()
        
        result['success'] = True
        result['message'] = _('Device unregistered successfully')
        result['data'] = {
            'user_id': user_id,
            'remote_id': remote_id
        }
        
        print(f"[DEVICE_UNREGISTER] 기기 삭제: {remote_id} ({user_id}) from {client_ip}")
        return JsonResponse(result, status=200)
        
    except Exception as e:
        result['success'] = False
        result['error'] = 'INTERNAL_ERROR'
        result['message'] = _('기기 등록 해제 중 오류가 발생했습니다: {}').format(str(e))
        print(f"[DEVICE_UNREGISTER] 오류: {str(e)}")
        return JsonResponse(result, status=500)


@csrf_exempt
def device_list(request, custom_id):
    """등록된 MDesk 기기 목록 조회 API (Bearer 토큰 인증 필요)
    
    엔드포인트: GET /api/device/list/<custom_id>
    인증: Bearer Token 필요
    
    응답 (성공):
    {
        "code": 1,
        "count": 3,
        "data": [
            {
                "remote_id": "ABC123456",
                "agent_id": "1",
                "hostname": "DESKTOP-XXX",
                "version": "1.4.9",
                "client_ip": "192.168.0.1",
                "is_active": true,
                "registered_at": "2026-01-08 12:34:56",
                "updated_at": "2026-01-08 12:34:56"
            },
            ...
        ]
    }
    
    응답 (실패):
    {
        "code": 0,
        "message": "에러 메시지"
    }
    """
    from django.conf import settings
    
    result = {}
    
    # 클라이언트 IP 확인 (로컬 테스트 모드용)
    client_ip = get_client_ip(request)
    is_local = client_ip in ['127.0.0.1', 'localhost', '::1']
    is_debug = getattr(settings, 'DEBUG', False)
    
    # 로컬 테스트 모드: DEBUG=True이고 로컬 IP인 경우 토큰 인증 건너뛰기
    if is_debug and is_local:
        token_user = UserProfile.objects.filter(username=custom_id).first()
        if not token_user:
            return JsonResponse({'code': 0, 'message': _('사용자를 찾을 수 없습니다.')}, status=404)
    else:
        # 토큰 인증
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'code': 0, 'message': _('인증 토큰이 없습니다.')}, status=401)
        
        access_token = auth_header.split(' ')[1]
        token_obj = RustDeskToken.objects.filter(access_token=access_token).first()
        
        if not token_obj:
            return JsonResponse({'code': 0, 'message': _('유효하지 않은 토큰입니다.')}, status=401)
        
        # 권한 확인 (토큰 주인과 요청받은 custom_id가 일치하는지)
        if token_obj.username != custom_id:
            return JsonResponse({'code': 0, 'message': _('권한이 없습니다.')}, status=403)
    
    try:
        # 최근 5분 기준 시간 계산
        from django.utils import timezone
        five_minutes_ago = timezone.now() - datetime.timedelta(minutes=5)
        
        # custom_id로 등록된 기기 목록 조회 (최근 5분 이내 updated_at 기준)
        devices = MdeskDeviceRegistration.objects.filter(
            custom_id=custom_id,
            updated_at__gte=five_minutes_ago
        ).order_by('-updated_at')
        
        device_list = []
        
        # custom_id로 UserProfile 조회하여 실제 user_pkid (UserProfile.id) 가져오기
        actual_user_pkid = ''
        try:
            user_profile = UserProfile.objects.get(username=custom_id)
            actual_user_pkid = str(user_profile.id)
        except UserProfile.DoesNotExist:
            pass
        
        for device in devices:
            device_list.append({
                'remote_id': device.remote_id,
                'user_pkid': actual_user_pkid,
                'agent_id': device.agent_id,
                'hostname': device.hostname,
                'version': device.version,
                'uuid': device.uuid,
                'client_ip': device.client_ip,
                'is_active': device.is_active,
                'registered_at': device.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': device.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        result['code'] = 1
        result['count'] = len(device_list)
        result['data'] = device_list
        
    except Exception as e:
        result['code'] = 0
        result['message'] = _('기기 목록 조회 중 오류가 발생했습니다: {}').format(str(e))
    
    return JsonResponse(result)


@csrf_exempt
def device_list_query(request):
    """등록된 MDesk 기기 목록 조회 API (쿼리 파라미터 방식)
    
    엔드포인트: GET /api/device/list?user_pkid=3 또는 ?user_id=imedix
    인증: Bearer Token (선택)
    
    쿼리 파라미터:
    - user_pkid: 사용자 고유 번호
    - user_id: 사용자 ID (username)
    - active_only: 1이면 최근 5분 이내 활성 기기만 조회 (기본값: 0, 모든 기기 조회)
    
    응답 (성공):
    {
        "success": true,
        "count": 3,
        "data": [...]
    }
    """
    from django.conf import settings
    
    result = {}
    
    # 쿼리 파라미터 추출
    user_pkid = request.GET.get('user_pkid', '')
    user_id = request.GET.get('user_id', '')
    active_only = request.GET.get('active_only', '0') == '1'
    
    if not user_pkid and not user_id:
        result['success'] = False
        result['error'] = 'MISSING_PARAMETER'
        result['message'] = _('user_pkid 또는 user_id 파라미터가 필요합니다.')
        return JsonResponse(result, status=400)
    
    try:
        # 필터 조건 구성
        query = Q()
        
        # active_only=1이면 최근 5분 이내 기기만 조회
        if active_only:
            from django.utils import timezone
            five_minutes_ago = timezone.now() - datetime.timedelta(minutes=5)
            query &= Q(updated_at__gte=five_minutes_ago)
        
        # user_pkid가 제공된 경우 UserProfile에서 username을 조회하여 custom_id로 매칭
        if user_pkid:
            try:
                user_profile = UserProfile.objects.get(id=int(user_pkid))
                query &= Q(custom_id=user_profile.username)
            except (UserProfile.DoesNotExist, ValueError):
                # 사용자를 찾을 수 없으면 빈 결과 반환
                result['success'] = True
                result['count'] = 0
                result['data'] = []
                return JsonResponse(result, status=200)
        elif user_id:
            query &= Q(custom_id=user_id)
        
        # 기기 목록 조회
        devices = MdeskDeviceRegistration.objects.filter(query).order_by('-updated_at')
        
        device_data = []
        for device in devices:
            # custom_id로 UserProfile 조회하여 실제 user_pkid (UserProfile.id) 가져오기
            actual_user_pkid = ''
            try:
                user_profile = UserProfile.objects.get(username=device.custom_id)
                actual_user_pkid = str(user_profile.id)
            except UserProfile.DoesNotExist:
                actual_user_pkid = device.user_pkid  # fallback
            
            device_data.append({
                'device_id': device.id,
                'remote_id': device.remote_id,
                'user_id': device.custom_id,
                'user_pkid': actual_user_pkid,
                'agent_id': device.agent_id,
                'alias': device.alias,
                'hostname': device.hostname,
                'platform': device.platform,
                'version': device.version,
                'uuid': device.uuid,
                'client_ip': device.client_ip,
                'is_active': device.is_active,
                'registered_at': device.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'updated_at': device.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            })
        
        result['success'] = True
        result['count'] = len(device_data)
        result['data'] = device_data
        return JsonResponse(result, status=200)
        
    except Exception as e:
        result['success'] = False
        result['error'] = 'INTERNAL_ERROR'
        result['message'] = _('기기 목록 조회 중 오류가 발생했습니다: {}').format(str(e))
        return JsonResponse(result, status=500)


@csrf_exempt
def certno_generate(request):
    """인증번호 발급 API (원격지에서 요청)
    
    엔드포인트: POST /api/certno/generate
    Content-Type: application/json
    
    요청 데이터:
    {
        "customer_id": "imedix",
        "user_pk_id": "42",
        "mdesk_id": "143165320"
    }
    
    성공 응답:
    {
        "success": true,
        "cert_code": "42123",
        "expires_at": "2026-01-16 14:40:25",
        "expires_in": 600
    }
    
    인증번호 생성 규칙:
    - user_pk_id가 있으면: user_pk_id + 3자리 랜덤숫자 (예: 42 + 123 = "42123")
    - user_pk_id가 없으면: 기존 방식 (3자리 랜덤숫자)
    
    실패 응답:
    {
        "success": false,
        "message": "에러 메시지"
    }
    """
    import random
    
    result = {}
    
    if request.method != 'POST':
        result['success'] = False
        result['message'] = _('POST 방식으로 요청하세요.')
        return JsonResponse(result, status=405)
    
    try:
        data = json.loads(request.body.decode())
    except:
        result['success'] = False
        result['message'] = _('잘못된 요청 형식입니다.')
        return JsonResponse(result, status=400)
    
    # 요청 데이터 추출 (모두 문자열로 통일)
    customer_id = str(data.get('customer_id', '')).strip()
    user_pk_id = str(data.get('user_pk_id', '')).strip()
    mdesk_id = str(data.get('mdesk_id', '')).strip()
    
    # 필수 필드 확인
    if not customer_id:
        result['success'] = False
        result['message'] = _('customer_id는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    if not mdesk_id:
        result['success'] = False
        result['message'] = _('mdesk_id는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    # 인증번호 생성: user_pk_id + 3자리 랜덤숫자 (예: 42 + 123 = "42123")
    # user_pk_id가 없으면 기존 방식 (3자리 랜덤)
    random_suffix = str(random.randint(100, 999))
    if user_pk_id:
        cert_code = f"{user_pk_id}{random_suffix}"
    else:
        cert_code = random_suffix
    
    # 캐시에 저장 (10분 = 600초 유효)
    expires_in = 600
    
    # 기존 방식 (customer_id + mdesk_id 조합)
    cache_key = f'certno_{customer_id}_{mdesk_id}'
    cache.set(cache_key, cert_code, expires_in)
    
    # cert_code 전용 캐시 (cert_code만으로 검증 가능)
    cert_only_key = f'certno_code_{cert_code}'
    cache.set(cert_only_key, {
        'customer_id': customer_id,
        'mdesk_id': mdesk_id,
        'user_pk_id': user_pk_id
    }, expires_in)
    
    # 역방향 캐시 저장 (customer_id + cert_code -> mdesk_id) - 삭제용
    reverse_cache_key = f'certno_reverse_{customer_id}_{cert_code}'
    cache.set(reverse_cache_key, mdesk_id, expires_in)
    
    # 디버깅 로그
    print(f"[CERTNO_GENERATE_DEBUG] cache_key={cache_key}, cert_only_key={cert_only_key}, cert_code={cert_code}")
    
    # 만료 시간 계산
    now = datetime.datetime.now()
    expires_at = now + datetime.timedelta(seconds=expires_in)
    
    print(f"[CERTNO_GENERATE] customer_id={customer_id}, mdesk_id={mdesk_id}, cert_code={cert_code}, expires_at={expires_at}")
    
    result['success'] = True
    result['cert_code'] = cert_code
    result['expires_at'] = expires_at.strftime('%Y-%m-%d %H:%M:%S')
    result['expires_in'] = expires_in
    
    return JsonResponse(result)


@csrf_exempt
def certno_delete(request):
    """인증번호 삭제 API
    
    엔드포인트: POST /api/certno/delete
    Content-Type: application/json
    
    요청 데이터:
    {
        "customer_id": "imedix",
        "cert_code": "420"
    }
    
    성공 응답:
    {
        "success": true,
        "message": "인증번호가 삭제되었습니다",
        "mdesk_id": "143165320"
    }
    
    실패 응답 (인증번호 없음):
    {
        "success": false,
        "message": "삭제할 인증번호가 없습니다"
    }
    """
    result = {}
    
    if request.method != 'POST':
        result['success'] = False
        result['message'] = _('POST 방식으로 요청하세요.')
        return JsonResponse(result, status=405)
    
    try:
        data = json.loads(request.body.decode())
    except:
        result['success'] = False
        result['message'] = _('잘못된 요청 형식입니다.')
        return JsonResponse(result, status=400)
    
    # 요청 데이터 추출 (모두 문자열로 통일)
    customer_id = str(data.get('customer_id', '')).strip()
    cert_code = str(data.get('cert_code', '')).strip()
    
    # 필수 필드 확인
    if not customer_id:
        result['success'] = False
        result['message'] = _('customer_id는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    if not cert_code:
        result['success'] = False
        result['message'] = _('cert_code는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    # 역방향 캐시에서 mdesk_id 조회
    reverse_cache_key = f'certno_reverse_{customer_id}_{cert_code}'
    mdesk_id = cache.get(reverse_cache_key)
    
    if mdesk_id:
        # 원본 캐시 키 삭제
        cache_key = f'certno_{customer_id}_{mdesk_id}'
        cache.delete(cache_key)
        # 역방향 캐시 키 삭제
        cache.delete(reverse_cache_key)
        
        print(f"[CERTNO_DELETE] customer_id={customer_id}, cert_code={cert_code}, mdesk_id={mdesk_id}, deleted")
        result['success'] = True
        result['message'] = _('인증번호가 삭제되었습니다')
        result['mdesk_id'] = mdesk_id
    else:
        print(f"[CERTNO_DELETE] reverse_key={reverse_cache_key}, not found")
        result['success'] = False
        result['message'] = _('삭제할 인증번호가 없습니다')
    
    return JsonResponse(result)


@csrf_exempt
def certno_cancel(request):
    """인증번호 취소 API (원격지에서 요청)
    
    엔드포인트: POST /api/certno/cancel
    Content-Type: application/json
    
    요청 데이터:
    {
        "customer_id": "imedix",
        "user_pk_id": "3",
        "mdesk_id": "5270854",
        "cert_code": "3813"
    }
    
    성공 응답:
    {
        "success": true,
        "message": "인증번호가 취소되었습니다",
        "data": {
            "customer_id": "imedix",
            "mdesk_id": "5270854",
            "cert_code": "3813"
        }
    }
    
    실패 응답:
    {
        "success": false,
        "error": "ERROR_CODE",
        "message": "에러 메시지"
    }
    """
    result = {}
    
    if request.method != 'POST':
        result['success'] = False
        result['error'] = 'METHOD_NOT_ALLOWED'
        result['message'] = _('POST 방식으로 요청하세요.')
        return JsonResponse(result, status=405)
    
    try:
        data = json.loads(request.body.decode())
    except:
        result['success'] = False
        result['error'] = 'INVALID_JSON'
        result['message'] = _('잘못된 요청 형식입니다.')
        return JsonResponse(result, status=400)
    
    # 요청 데이터 추출 (모두 문자열로 통일)
    customer_id = str(data.get('customer_id', '')).strip()
    user_pk_id = str(data.get('user_pk_id', '')).strip()
    mdesk_id = str(data.get('mdesk_id', '')).strip()
    cert_code = str(data.get('cert_code', '')).strip()
    
    # 필수 필드 확인
    if not customer_id:
        result['success'] = False
        result['error'] = 'MISSING_CUSTOMER_ID'
        result['message'] = _('customer_id는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    if not mdesk_id:
        result['success'] = False
        result['error'] = 'MISSING_MDESK_ID'
        result['message'] = _('mdesk_id는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    if not cert_code:
        result['success'] = False
        result['error'] = 'MISSING_CERT_CODE'
        result['message'] = _('cert_code는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    # 캐시 키 정의
    cache_key = f'certno_{customer_id}_{mdesk_id}'
    cert_only_key = f'certno_code_{cert_code}'
    reverse_cache_key = f'certno_reverse_{customer_id}_{cert_code}'
    
    # 인증번호 검증 (저장된 값과 일치하는지 확인)
    stored_cert_code = cache.get(cache_key)
    
    if not stored_cert_code:
        result['success'] = False
        result['error'] = 'CERT_NOT_FOUND'
        result['message'] = _('취소할 인증번호가 없습니다.')
        print(f"[CERTNO_CANCEL] cache_key={cache_key}, not found")
        return JsonResponse(result, status=404)
    
    if stored_cert_code != cert_code:
        result['success'] = False
        result['error'] = 'CERT_MISMATCH'
        result['message'] = _('인증번호가 일치하지 않습니다.')
        print(f"[CERTNO_CANCEL] cert_code mismatch: stored={stored_cert_code}, requested={cert_code}")
        return JsonResponse(result, status=400)
    
    # 모든 관련 캐시 삭제
    cache.delete(cache_key)           # certno_{customer_id}_{mdesk_id}
    cache.delete(cert_only_key)       # certno_code_{cert_code}
    cache.delete(reverse_cache_key)   # certno_reverse_{customer_id}_{cert_code}
    
    print(f"[CERTNO_CANCEL] 인증번호 취소: customer_id={customer_id}, mdesk_id={mdesk_id}, cert_code={cert_code}")
    
    result['success'] = True
    result['message'] = _('인증번호가 취소되었습니다')
    result['data'] = {
        'customer_id': customer_id,
        'mdesk_id': mdesk_id,
        'cert_code': cert_code
    }
    
    return JsonResponse(result)


@csrf_exempt
def certno_search(request):
    """인증번호 조회 API
    
    엔드포인트: POST /api/certno/search
    Content-Type: application/json
    
    요청 데이터:
    {
        "customer_id": "imedix",
        "mdesk_id": "143165320"
    }
    
    성공 응답 (인증번호 있음):
    {
        "success": true,
        "cert_code": "420",
        "exists": true
    }
    
    응답 (인증번호 없음):
    {
        "success": true,
        "cert_code": null,
        "exists": false
    }
    """
    result = {}
    
    if request.method != 'POST':
        result['success'] = False
        result['message'] = _('POST 방식으로 요청하세요.')
        return JsonResponse(result, status=405)
    
    try:
        data = json.loads(request.body.decode())
    except:
        result['success'] = False
        result['message'] = _('잘못된 요청 형식입니다.')
        return JsonResponse(result, status=400)
    
    # 요청 데이터 추출 (모두 문자열로 통일)
    customer_id = str(data.get('customer_id', '')).strip()
    mdesk_id = str(data.get('mdesk_id', '')).strip()
    
    # 필수 필드 확인
    if not customer_id:
        result['success'] = False
        result['message'] = _('customer_id는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    if not mdesk_id:
        result['success'] = False
        result['message'] = _('mdesk_id는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    # 캐시에서 인증번호 조회
    cache_key = f'certno_{customer_id}_{mdesk_id}'
    stored_code = cache.get(cache_key)
    
    print(f"[CERTNO_SEARCH] cache_key={cache_key}, stored_code={stored_code}")
    
    result['success'] = True
    result['cert_code'] = stored_code
    result['exists'] = stored_code is not None
    
    return JsonResponse(result)


@csrf_exempt
def certno_verify(request):
    """인증번호 검증 API (원격지에서 요청)
    
    엔드포인트: POST /api/certno/verify
    Content-Type: application/json
    
    요청 데이터 (cert_code만 필수):
    {
        "cert_code": "42847291",
        "peer_id": "143165320"
    }
    
    cert_code: user_pk_id + 6자리 랜덤숫자 (예: "42847291")
    peer_id: 피제어자 ID (원격 받는 쪽)
    
    검증 우선순위:
    1. cert_code만으로 검증 (권장)
    2. customer_id + peer_id + cert_code 조합 (폴백)
    3. 사용자 휴대전화/이메일 인증번호 (폴백)
    
    성공 응답:
    {
        "success": true,
        "message": "인증 완료",
        "verified_at": "2026-01-20 15:30:00",
        "customer_id": "imedix",
        "peer_id": "143165320"
    }
    
    실패 응답:
    {
        "success": false,
        "message": "인증번호가 올바르지 않습니다"
    }
    """
    result = {}
    
    if request.method != 'POST':
        result['success'] = False
        result['message'] = _('POST 방식으로 요청하세요.')
        return JsonResponse(result, status=405)
    
    # 클라이언트 IP
    client_ip = get_client_ip(request)
    
    try:
        data = json.loads(request.body.decode())
    except:
        result['success'] = False
        result['message'] = _('잘못된 요청 형식입니다.')
        return JsonResponse(result, status=400)
    
    # 요청 데이터 추출 (모두 문자열로 통일)
    customer_id = str(data.get('customer_id', '')).strip()
    # peer_id 우선, mdesk_id는 하위호환
    peer_id = str(data.get('peer_id', data.get('mdesk_id', ''))).strip()
    cert_code = str(data.get('cert_code', '')).strip()
    device_info = data.get('device_info', {})
    
    hostname = device_info.get('hostname', '') if isinstance(device_info, dict) else ''
    uuid = device_info.get('uuid', '') if isinstance(device_info, dict) else ''
    version = device_info.get('version', '') if isinstance(device_info, dict) else ''
    
    # 필수 필드 확인 (cert_code만 필수, customer_id/mdesk_id는 선택)
    if not cert_code:
        result['success'] = False
        result['message'] = _('cert_code는 필수 항목입니다.')
        return JsonResponse(result, status=400)
    
    # 인증번호 검증 로직
    is_verified = False
    message = _('인증번호가 올바르지 않습니다')
    verified_customer_id = customer_id  # 검증된 customer_id (cert_code에서 추출 가능)
    verified_peer_id = peer_id  # 검증된 peer_id
    
    # 1. cert_code 전용 캐시로 검증 (cert_code만으로 검증)
    cert_only_key = f'certno_code_{cert_code}'
    cert_data = cache.get(cert_only_key)
    verified_user_pk_id = None  # cert_data에서 추출할 user_pk_id
    
    # 디버깅 로그
    print(f"[CERTNO_VERIFY_DEBUG] cert_only_key={cert_only_key}, cert_data={cert_data}, input_code={cert_code}")
    
    if cert_data:
        is_verified = True
        message = _('인증 완료')
        # 캐시에서 customer_id, peer_id(mdesk_id), user_pk_id 추출 (요청에 없어도 됨)
        verified_customer_id = cert_data.get('customer_id', customer_id)
        verified_peer_id = cert_data.get('mdesk_id', peer_id)  # 캐시는 mdesk_id로 저장됨
        verified_user_pk_id = cert_data.get('user_pk_id', None)
        # 캐시 삭제
        cache.delete(cert_only_key)
        # 기존 캐시도 삭제
        old_cache_key = f'certno_{verified_customer_id}_{verified_peer_id}'
        cache.delete(old_cache_key)
    else:
        # 2. 기존 방식: customer_id + peer_id 조합으로 확인 (폴백)
        cache_key = f'certno_{customer_id}_{peer_id}'
        stored_code = cache.get(cache_key)
        
        if stored_code and str(stored_code).strip() == str(cert_code).strip():
            is_verified = True
            message = _('인증 완료')
            cache.delete(cache_key)
        else:
            # 3. 사용자 휴대전화/이메일 인증번호 확인 (폴백)
            user = UserProfile.objects.filter(username=customer_id).first()
            
            if user:
                # 휴대전화 인증번호 확인
                if user.phone:
                    phone_cache_key = f'verify_code_{user.phone}'
                    phone_stored_code = cache.get(phone_cache_key)
                    if phone_stored_code and phone_stored_code == cert_code:
                        is_verified = True
                        message = _('인증 완료')
                        cache.delete(phone_cache_key)
                
                # 이메일 인증번호 확인
                if not is_verified and user.email:
                    email_cache_key = f'verify_code_email_{user.email}'
                    email_stored_code = cache.get(email_cache_key)
                    if email_stored_code and email_stored_code == cert_code:
                        is_verified = True
                        message = _('인증 완료')
                        cache.delete(email_cache_key)
    
    # customer_id, peer_id가 비어있으면 검증된 값으로 대체
    if not customer_id:
        customer_id = verified_customer_id
    if not peer_id:
        peer_id = verified_peer_id
    
    # 검증 기록 저장
    now = datetime.datetime.now()
    verification = CertNoVerification.objects.create(
        customer_id=customer_id,
        mdesk_id=peer_id,  # DB 필드명은 mdesk_id 유지
        cert_code=cert_code,
        hostname=hostname,
        uuid=uuid,
        version=version,
        client_ip=client_ip,
        is_verified=is_verified
    )
    
    print(f"[CERTNO_VERIFY] customer_id={customer_id}, peer_id={peer_id}, cert_code={cert_code}, verified={is_verified}, ip={client_ip}")
    
    result['success'] = is_verified
    result['message'] = message
    if is_verified:
        result['verified_at'] = now.strftime('%Y-%m-%d %H:%M:%S')
        result['customer_id'] = customer_id
        result['peer_id'] = peer_id
    
    return JsonResponse(result)


def download_client(request, customer_id):
    """클라이언트 다운로드 API
    
    엔드포인트: GET /api/download/{customer_id}
    쿼리: certnum (선택) - 인증번호
    
    파일명 형식: MDesk_portable-id={customer_id},certno=true[,certnum=인증번호].exe
    """
    from django.conf import settings
    
    # 실행파일 경로
    executable_dir = getattr(settings, 'EXECUTABLE_DIR', os.path.join(settings.BASE_DIR, 'executables'))
    file_path = os.path.join(executable_dir, 'MDesk_portable.exe')
    
    if not os.path.exists(file_path):
        raise Http404("파일을 찾을 수 없습니다.")
    
    # 다운로드 파일명 설정 (certnum 있으면 추가)
    download_filename = f'MDesk_portable-id={customer_id},certno=true'
    certnum = request.GET.get('certnum', '').strip()
    if certnum:
        download_filename += f',certnum={certnum}'
    download_filename += '.exe'
    
    response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=download_filename)
    return response
