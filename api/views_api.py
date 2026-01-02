# cython:language_level=3
from django.http import JsonResponse
import json
import time
import datetime
# import hashlib
import math
from django.contrib import auth
# from django.forms.models import model_to_dict
from api.models import RustDeskToken, UserProfile, RustDeskTag, RustDeskPeer, RustDesDevice, ConnLog, FileLog, CustomAppConfig, SupportAgent, AgentConnectionLog
from django.db.models import Q
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
    # 绑定设备  20240819
    peer = RustDeskPeer.objects.filter(Q(rid=rid)).first()
    if not peer:
        device = RustDesDevice.objects.filter(Q(uuid=uuid)).first()
        if device:
            peer = RustDeskPeer()
            peer.uid = user.id
            peer.rid = device.rid
            # peer.abid = ab.guid    # v2,  current version not used
            peer.hostname = device.hostname
            peer.username = device.username
            peer.save()

    token = RustDeskToken.objects.filter(Q(uid=user.id) & Q(username=user.username) & Q(rid=user.rid)).first()

    # 检查是否过期
    if token:
        now_t = datetime.datetime.now()
        nums = (now_t - token.create_time).seconds if now_t > token.create_time else 0
        if nums >= EFFECTIVE_SECONDS:
            token.delete()
            token = None

    if not token:
        # 获取并保存token
        token = RustDeskToken(
            username=user.username,
            uid=user.id,
            uuid=user.uuid,
            rid=user.rid,
            access_token=getStrMd5(str(time.time()) + salt)
        )
        token.save()

    result['access_token'] = token.access_token
    result['type'] = 'access_token'
    result['user'] = {
        'user_pkid': user.id,
        'name': user.username,
        'email': user.email,
        'phone': user.phone,
        'company_name': user.company_name,
        'membership_level': user.membership_level,
        'membership_start': user.membership_start.isoformat() if user.membership_start else None,
        'membership_expires': user.membership_expires.isoformat() if user.membership_expires else None,
        'max_agents': user.max_agents,
        'is_admin': user.is_admin,
    }
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
    token = RustDeskToken.objects.filter(Q(access_token=access_token)).first()
    user = None
    if token:
        user = UserProfile.objects.filter(Q(id=token.uid)).first()

    if user:
        if token:
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
        'is_admin': user.is_admin,
        'is_active': user.is_active,
    }
    return JsonResponse(result)


def ab(request):
    '''
    '''
    access_token = request.META.get('HTTP_AUTHORIZATION', '')
    access_token = access_token.split('Bearer ')[-1]
    token = RustDeskToken.objects.filter(Q(access_token=access_token)).first()
    if not token:
        result = {'error': _('목록 가져오기 오류!')}
        return JsonResponse(result)

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

        result['updated_at'] = datetime.datetime.now()
        result['data'] = {
            'tags': tag_names,
            'peers': peers_result,
            'tag_colors': json.dumps(tag_colors)
        }
        result['data'] = json.dumps(result['data'])
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
    postdata = json.loads(request.body)
    device = RustDesDevice.objects.filter(Q(rid=postdata['id']) & Q(uuid=postdata['uuid'])).first()
    if device:
        client_ip = get_client_ip(request)
        device.ip_address = client_ip
        device.save()
    # token保活
    create_time = datetime.datetime.now() + datetime.timedelta(seconds=EFFECTIVE_SECONDS)
    RustDeskToken.objects.filter(Q(rid=postdata['id']) & Q(uuid=postdata['uuid'])).update(create_time=create_time)
    result = {}
    result['data'] = _('온라인')
    return JsonResponse(result)


def audit(request):
    postdata = json.loads(request.body)
    # print(postdata)
    audit_type = postdata['action'] if 'action' in postdata else ''
    if audit_type == 'new':
        new_conn_log = ConnLog(
            action=postdata['action'] if 'action' in postdata else '',
            conn_id=postdata['conn_id'] if 'conn_id' in postdata else 0,
            from_ip=postdata['ip'] if 'ip' in postdata else '',
            from_id='',
            rid=postdata['id'] if 'id' in postdata else '',
            conn_start=datetime.datetime.now(),
            session_id=postdata['session_id'] if 'session_id' in postdata else 0,
            uuid=postdata['uuid'] if 'uuid' in postdata else '',
        )
        new_conn_log.save()
    elif audit_type == "close":
        ConnLog.objects.filter(Q(conn_id=postdata['conn_id'])).update(conn_end=datetime.datetime.now())
    elif 'is_file' in postdata:
        print(postdata)
        files = json.loads(postdata['info'])['files']
        filesize = convert_filesize(int(files[0][1]))
        new_file_log = FileLog(
            file=postdata['path'],
            user_id=postdata['peer_id'],
            user_ip=json.loads(postdata['info'])['ip'],
            remote_id=postdata['id'],
            filesize=filesize,
            direction=postdata['type'],
            logged_at=datetime.datetime.now(),
        )
        new_file_log.save()
    else:
        try:
            peer = postdata['peer']
            ConnLog.objects.filter(Q(conn_id=postdata['conn_id'])).update(session_id=postdata['session_id'])
            ConnLog.objects.filter(Q(conn_id=postdata['conn_id'])).update(from_id=peer[0])
        except Exception as e:
            print(postdata, e)

    result = {
        'code': 1,
        'data': 'ok'
    }
    return JsonResponse(result)


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
    보안: Bearer Token 인증
    """
    result = {}
    
    # [디버그] 요청 정보 출력
    print(f"\n[ADD_AGENT_DEBUG] 요청된 username: {username}")
    
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
    
    for agent in agents:
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
    print(f"[AGENT_CLOSE_LOG] 결과: 성공")
    
    return JsonResponse({
        'code': 1,
        'msg': 'Agent closed successfully',
        'data': {
            'userid': userid,
            'agentid': agent_num,
            'agent_deleted': agent_deleted,
            'logs_deleted': deleted_logs
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
    
    if not custom_config:
        # 기본값 반환
        result['code'] = 1
        result['data'] = {
            'app_name': 'MDesk',
            'logo_url': '',
            'password': '',
            'encrypted_password': '',
            'title': 'Your Desktop',
            'description': 'Your desktop can be accessed with this ID and password.'
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
