# 커스텀 앱 설정 API 문서

## API 명칭
**`/api/custom_app_config`**

## 설명
RustDesk 클라이언트에서 사용자의 커스텀 앱 설정 정보를 가져올 수 있는 API입니다.

## 요청 방식
- **Method**: `POST`
- **Content-Type**: `application/json`
- **인증**: username (로그인 아이디) 사용

## 요청 Body
```json
{
    "username": "your_login_username"
}
```

## 요청 예시

### cURL
```bash
curl -X POST http://your-domain.com:21114/api/custom_app_config \
  -H "Content-Type: application/json" \
  -d '{"username": "your_login_username"}'
```

### Python (requests)
```python
import requests
import json

url = "http://your-domain.com:21114/api/custom_app_config"
headers = {
    "Content-Type": "application/json"
}
data = {
    "username": "your_login_username"  # 로그인 아이디
}

response = requests.post(url, headers=headers, json=data)
result = response.json()

if result.get('code') == 1:
    config = result['data']
    print(f"앱 이름: {config['app_name']}")
    print(f"로고 URL: {config['logo_url']}")
    print(f"암호화된 암호: {config['encrypted_password']}")
else:
    print(f"오류: {result.get('error')}")
```

### JavaScript (fetch)
```javascript
fetch('http://your-domain.com:21114/api/custom_app_config', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        username: 'your_login_username'  // 로그인 아이디
    })
})
.then(response => response.json())
.then(data => {
    if (data.code === 1) {
        console.log('앱 이름:', data.data.app_name);
        console.log('로고 URL:', data.data.logo_url);
        console.log('암호화된 암호:', data.data.encrypted_password);
    } else {
        console.error('오류:', data.error);
    }
})
.catch(error => {
    console.error('Error:', error);
});
```

### RustDesk 클라이언트 예시
```python
# RustDesk 클라이언트에서 사용 예시
import requests
import json

def get_custom_app_config(api_server, username):
    """
    커스텀 앱 설정 정보 가져오기
    
    Args:
        api_server: API 서버 주소 (예: http://your-domain.com:21114)
        username: 로그인 아이디
    
    Returns:
        dict: 커스텀 앱 설정 정보
    """
    url = f"{api_server}/api/custom_app_config"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "username": username
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API 요청 오류: {e}")
        return None

# 사용 예시
api_server = "http://your-domain.com:21114"
username = "imedix"  # 로그인 아이디

result = get_custom_app_config(api_server, username)
if result and result.get('code') == 1:
    config = result['data']
    print(f"앱 이름: {config['app_name']}")
    print(f"로고 URL: {config['logo_url']}")
    print(f"암호화된 암호: {config['encrypted_password']}")
    print(f"제목: {config['title']}")
    print(f"설명: {config['description']}")
else:
    print(f"오류: {result.get('error', '알 수 없는 오류')}")
```

## 응답 형식

### 성공 응답 (200 OK)
```json
{
    "code": 1,
    "data": {
        "app_name": "MDesk",
        "logo_url": "http://your-domain.com:21114/media/custom_logos/logo.png",
        "password": "1234",
        "encrypted_password": "BwcXBA",
        "title": "Your Desktop",
        "description": "Your desktop can be accessed with this ID and password.",
        "created_at": "2024-01-01 12:00:00",
        "updated_at": "2024-01-01 12:30:00"
    }
}
```

### 설정이 없는 경우 (기본값 반환)
```json
{
    "code": 1,
    "data": {
        "app_name": "MDesk",
        "logo_url": "",
        "password": "",
        "encrypted_password": "",
        "title": "Your Desktop",
        "description": "Your desktop can be accessed with this ID and password."
    }
}
```

### 오류 응답
```json
{
    "error": "username이 필요합니다!"
}
```

또는

```json
{
    "error": "해당 사용자를 찾을 수 없습니다! (username 확인 필요)"
}
```

또는

```json
{
    "error": "잘못된 제출 방식! POST 방식을 사용하세요."
}
```

## 응답 필드 설명

| 필드명 | 타입 | 설명 |
|--------|------|------|
| `code` | integer | 응답 코드 (1: 성공) |
| `data` | object | 커스텀 앱 설정 데이터 |
| `data.app_name` | string | 앱 이름 |
| `data.logo_url` | string | 로고 이미지 URL (절대 경로) |
| `data.password` | string | 원본 암호 (필요시 사용) |
| `data.encrypted_password` | string | 암호화된 암호 (RustDesk 클라이언트에서 사용) |
| `data.title` | string | 제목 |
| `data.description` | string | 설명 |
| `data.created_at` | string | 생성 시간 (YYYY-MM-DD HH:MM:SS) |
| `data.updated_at` | string | 수정 시간 (YYYY-MM-DD HH:MM:SS) |
| `error` | string | 오류 메시지 (오류 발생 시) |

## 인증 토큰 받기

인증 토큰은 `/api/login` API를 통해 받을 수 있습니다.

### 로그인 API 예시
```bash
curl -X POST http://your-domain.com:21114/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password",
    "id": "your_rustdesk_id",
    "uuid": "your_uuid"
  }'
```

응답:
```json
{
    "access_token": "abc123def456...",
    "type": "access_token",
    "user": {
        "name": "your_username"
    }
}
```

## 주의사항

1. **키값**: POST body에 `username` (로그인 아이디)를 전달해야 합니다.
2. **POST 방식**: GET 요청은 지원하지 않으며, POST 방식만 사용 가능합니다.
3. **암호화된 암호**: `encrypted_password`는 RustDesk 클라이언트에서 사용할 수 있도록 암호화된 형태입니다.
4. **로고 URL**: 로고가 설정되지 않은 경우 `logo_url`은 빈 문자열입니다.
5. **기본값**: 사용자가 설정을 저장하지 않은 경우 기본값이 반환됩니다.
6. **사용자 찾기**: `username`으로 사용자를 찾으며, 사용자를 찾을 수 없는 경우 오류가 반환됩니다.

## 관련 API

- `/api/login`: 로그인 및 토큰 발급
- `/api/custom_app`: 웹 UI에서 커스텀 앱 설정 관리 (웹 브라우저용)
- `/api/agentnumupdate/<userid>/<mdeskid>?agentid=11`: 상담원 접속 정보 업데이트 API
- `/api/<username>/addnum`: 상담원 추가 API
- `/api/<username>/delnum/<agent_num>`: 상담원 삭제 API
- `/api/<username>/agents`: 상담원 목록 조회 API

## 상담원 추가 API

### API 명칭
**`/api/<username>/addnum`**

### 설명
새로운 상담원을 자동으로 번호를 매겨 추가하는 API입니다.

### 요청 방식
- **Method**: `GET` (또는 POST)
- **인증**: Bearer Token 인증 (`Authorization: Bearer <token>`)

### 요청 예시 (cURL)
```bash
curl -X GET http://your-domain.com:21114/api/imedix/addnum \
  -H "Authorization: Bearer your_access_token_here"
```

### 성공 응답 (200 OK)
```json
{
    "code": 1,
    "msg": "상담원이 성공적으로 추가되었습니다.",
    "data": {
        "agent_num": 3,
        "agent_name": "상담원 3"
    }
}
```

---

## 상담원 삭제 API

### API 명칭
**`/api/<username>/delnum/<agent_num>`**

### 설명
특정 번호의 상담원을 삭제하는 API입니다.

### 요청 방식
- **Method**: `GET` (또는 DELETE)
- **인증**: Bearer Token 인증 (`Authorization: Bearer <token>`)

### 요청 예시 (cURL)
```bash
# imedix 사용자의 1번 상담원 삭제
curl -X GET http://your-domain.com:21114/api/imedix/delnum/1 \
  -H "Authorization: Bearer your_access_token_here"
```

### 성공 응답 (200 OK)
```json
{
    "code": 1,
    "msg": "상담원이 성공적으로 삭제되었습니다."
}
```

---

## 상담원 목록 조회 API

### API 명칭
**`/api/<username>/agents`**

### 설명
해당 사용자에 등록된 모든 상담원 리스트를 가져오는 API입니다.

### 요청 방식
- **Method**: `GET`
- **인증**: Bearer Token 인증 (`Authorization: Bearer <token>`)

### 요청 예시 (cURL)
```bash
curl -X GET http://your-domain.com:21114/api/imedix/agents \
  -H "Authorization: Bearer your_access_token_here"
```

### 성공 응답 (200 OK)
```json
{
    "code": 1,
    "data": [
        {
            "agent_num": 1,
            "agent_name": "상담원 1",
            "create_time": "2024-01-01 12:00:00"
        },
        {
            "agent_num": 2,
            "agent_name": "상담원 2",
            "create_time": "2024-01-01 12:05:00"
        }
    ]
}
```

---

## 상담원 접속 정보 업데이트 API

### API 명칭
**`/api/agentnumupdate/<userid>/<mdeskid>?agentid=11`**

### 설명
특정 사용자의 MDesk ID가 최근에 어떤 상담원 번호로 접속했는지 기록합니다. 하루에 동일한 상담원 번호 조합은 중복 저장되지 않습니다.

### 요청 방식
- **Method**: `GET`
- **URL Parameter**:
    - `userid`: 관리자/사용자 아이디 (예: imedix)
    - `mdeskid`: 접속한 클라이언트의 MDesk ID (RustDesk ID)
- **Query Parameter**:
    - `agentid`: 상담원 번호 (예: 11)

### 요청 예시 (cURL)
```bash
curl -X GET "http://your-domain.com:21114/api/agentnumupdate/imedix/client_mdeskid?agentid=11"
```

### 성공 응답 (200 OK)
```json
{
    "code": 1,
    "msg": "Registered successfully",
    "data": {
        "userid": "imedix",
        "mdeskid": "client_mdeskid",
        "agentid": 11
    }
}
```

