# MDesk API Server (RustDesk API Server)

이 프로젝트는 Python Django 기반의 RustDesk API 서버입니다. 웹 관리 페이지(Web UI)를 통해 기기 관리, 사용자 관리, 그리고 커스텀 실행파일 배포 기능을 제공합니다.

현재 이 프로젝트는 **PostgreSQL** 데이터베이스와 **Docker** 배포 환경에 최적화되어 있습니다.

---

## 주요 기능

- **RustDesk API 연동**: 주소록 연동, 기기 상태 확인, 하트비트 관리.
- **웹 관리 콘솔**: 기기 목록 조회, 연결 로그, 파일 전송 로그 확인.
- **사용자 맞춤 설정**: `admin.787.kr` 도메인을 통한 관리자 기능 격리.
- **커스텀 앱 배포**: 사용자별 설정이 반영된 `MDesk_portable.exe` 생성 및 다운로드.
- **SSL/HTTPS 지원**: Nginx 리버스 프록시를 통한 안전한 접속 및 SSL 인증 지원.
- **자동화 스크립트**: 이미지 빌드, 저장, 배포를 위한 배치 파일 제공.

---

## 시작하기 (배포 가이드)

### 1. 환경 설정 (.env)
프로젝트 루트의 `env_config.txt`를 `.env`로 이름을 변경하고 환경에 맞게 수정합니다.

```env

# ============== 기본설정 ============== 
HOST=0.0.0.0 
TZ=Asia/Seoul 
 
# ============== Django 설정 ============== 
SECRET_KEY=너꺼 키
DEBUG=False
LANGUAGE_CODE=ko
ALLOW_REGISTRATION=True
ID_SERVER=도메인주소 만드세요
CSRF_TRUSTED_ORIGINS=도메인주소 만드세요,도메인주소 만드세요,도메인주소 만드세요,도메인주소 만드세요 형식
 
# ============== 데이터베이스 설정 ============== 
DATABASE_TYPE=POSTGRESQL
POSTGRES_DBNAME=
POSTGRES_HOST=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_PORT=5432
 
# ============== 이메일설정 ============== 
EMAIL_HOST=smtp.gmail.com 
EMAIL_PORT=587 
EMAIL_USE_TLS=True 
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
 
# ============== 카카오알림톡 설정(옵션) ============== 
KAKAO_ALIMTALK_API_URL=비즈톡API 추천드려요(기업만가능한걸로알고있음)
KAKAO_ALIMTALK_ID=
KAKAO_ALIMTALK_PW=
KAKAO_ALIMTALK_TEM_NUM=카카오비즈니스 키받아서 올리시고
KAKAO_ALIMTALK_SEND_NUM=발신번호
```

### 2. 도커 배포 (Windows)
제공된 배치 파일을 실행하여 즉시 배포합니다.
- `deploy.bat`: 현재 소스 기준으로 컨테이너 빌드 및 실행.
- `save_image.bat`: 다른 서버 배포를 위해 이미지를 `.tar` 파일로 추출.

### 3. 다른 서버로 이전 배포
1. 원본 PC에서 `save_image.bat` 실행 -> `rustdesk_image.tar` 생성.
2. 서버로 `rustdesk_image.tar`, `docker-compose.yaml`, `.env` 복사.
3. 서버에서 이미지 로드 및 실행:
   ```cmd
   docker load -i rustdesk_image.tar
   docker-compose up -d
   ```

---

## 네트워크 및 SSL 설정

### 포트 구성
- **HTTP (80)**: 웹 서비스 및 API 통신용.
- **HTTPS (443)**: SSL 보안 접속용 (Nginx 설정 시).

### SSL 인증 (HTTP-01)
SSL 인증을 위한 챌린지 파일은 아래 경로에 넣으면 외부에서 즉시 접근 가능합니다.
- 호스트 경로: `./.well-known/pki-validation/`
- 접속 주소: `http://787.kr/.well-known/pki-validation/파일명.txt`

---

## 프로젝트 구조

- `api/`: 핵심 API 및 비즈니스 로직.
- `webui/`: 웹 클라이언트(Flutter 기반) 서빙 서비스.
- `static/`: 정적 파일 (favicon.ico, CSS, JS).
- `executables/`: 배포용 실행파일 저장소 (볼륨 연결 권장).
- `nginx.conf`: SSL 및 리버스 프록시 설정 파일.

---

## 개발 및 관리 스크립트

- `git_push.bat`: 변경 사항을 GitHub(`metadtlab/MDesk`)로 즉시 푸시.
- `manage.py`: Django 관리 명령어 실행.

---

## 주의사항
- **Pillow**: 이미지 필드 사용을 위해 Docker 빌드 시 자동으로 설치됩니다.
- **CSRF**: 외부 도메인 접속 시 `CSRF_TRUSTED_ORIGINS` 설정을 반드시 확인하세요.
- **데이터 저장**: `./db`, `./media`, `./executables` 폴더는 도커 볼륨으로 연결되어 데이터가 보존됩니다.
