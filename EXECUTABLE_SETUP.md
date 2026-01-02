# 실행파일 다운로드 설정 가이드

## 실행파일 저장 위치

실행파일은 다음 디렉토리에 저장해야 합니다:

**경로**: `D:\IMedix\Python\rustdesk-api-server\executables\`

## 파일명 형식

템플릿 파일명: `rustdesk_portable-id=admin.exe`

이 파일이 `executables` 폴더에 있어야 합니다.

## 설정 방법

1. **executables 폴더 생성** (자동 생성됨)
   ```
   D:\IMedix\Python\rustdesk-api-server\executables\
   ```

2. **실행파일 복사**
   - `rustdesk_portable-id=admin.exe` 파일을 `executables` 폴더에 복사합니다.
   - 또는 다른 이름의 RustDesk 실행파일을 복사하고 이름을 변경합니다.

3. **지원되는 파일명** (우선순위 순)
   - `rustdesk_portable-id=admin.exe` (기본)
   - `rustdesk_portable.exe`
   - `rustdesk.exe`

## 다운로드 동작

사용자가 "실행파일 다운로드" 버튼을 클릭하면:

1. 로그인한 사용자의 `username`을 가져옵니다.
2. 파일명을 `rustdesk_portable-id={username}.exe` 형식으로 생성합니다.
   - 예: 사용자명이 "imedix"인 경우 → `rustdesk_portable-id=imedix.exe`
3. 템플릿 파일을 읽어서 사용자별 파일명으로 다운로드합니다.

## 설정 파일 위치

`rustdesk_server_api/settings.py`에서 다음 설정을 확인할 수 있습니다:

```python
# 실행파일 저장 경로
EXECUTABLE_DIR = os.path.join(BASE_DIR, 'executables')
EXECUTABLE_TEMPLATE = 'rustdesk_portable-id={username}.exe'  # 템플릿 파일명
```

## 주의사항

- 실행파일이 없으면 다운로드 시 오류 메시지가 표시됩니다.
- 실행파일은 실제 RustDesk 포터블 실행파일이어야 합니다.
- 파일 크기가 큰 경우 다운로드 시간이 걸릴 수 있습니다.

