# 이메일 발송 설정 가이드

## 환경변수 설정

실제 이메일로 인증번호 및 비밀번호 재설정 링크를 발송하려면 다음 환경변수를 설정하세요.

### Windows (Command Prompt)
```cmd
set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
set EMAIL_HOST=smtp.gmail.com
set EMAIL_PORT=587
set EMAIL_USE_TLS=True
set EMAIL_HOST_USER=your-email@gmail.com
set EMAIL_HOST_PASSWORD=your-app-password
set DEFAULT_FROM_EMAIL=your-email@gmail.com
```

### Linux/Mac
```bash
export EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
export EMAIL_HOST=smtp.gmail.com
export EMAIL_PORT=587
export EMAIL_USE_TLS=True
export EMAIL_HOST_USER=your-email@gmail.com
export EMAIL_HOST_PASSWORD=your-app-password
export DEFAULT_FROM_EMAIL=your-email@gmail.com
```

## Gmail 사용 시 주의사항

1. **앱 비밀번호 생성 필요**
   - Gmail 계정에서 2단계 인증을 활성화해야 합니다.
   - Google 계정 설정 > 보안 > 2단계 인증 > 앱 비밀번호에서 앱 비밀번호를 생성하세요.
   - 일반 비밀번호가 아닌 **앱 비밀번호**를 사용해야 합니다.

2. **Gmail SMTP 설정**
   - `EMAIL_HOST`: `smtp.gmail.com`
   - `EMAIL_PORT`: `587` (TLS) 또는 `465` (SSL)
   - `EMAIL_USE_TLS`: `True` (포트 587 사용 시)
   - `EMAIL_USE_SSL`: `True` (포트 465 사용 시)

## 다른 이메일 서비스 설정 예시

### Outlook/Hotmail
```cmd
set EMAIL_HOST=smtp-mail.outlook.com
set EMAIL_PORT=587
set EMAIL_USE_TLS=True
```

### 네이버 메일
```cmd
set EMAIL_HOST=smtp.naver.com
set EMAIL_PORT=587
set EMAIL_USE_TLS=True
```

### 다음(Daum) 메일
```cmd
set EMAIL_HOST=smtp.daum.net
set EMAIL_PORT=465
set EMAIL_USE_SSL=True
```

## 테스트 방법

1. 환경변수 설정 후 Django 서버 재시작
2. 회원가입 또는 비밀번호 찾기 페이지에서 이메일 입력
3. 실제 이메일 수신함 확인

## 문제 해결

### 이메일이 발송되지 않는 경우
1. 환경변수가 올바르게 설정되었는지 확인
2. 이메일 서버의 SMTP 설정 확인
3. 방화벽에서 SMTP 포트(587, 465) 차단 여부 확인
4. Gmail 사용 시 앱 비밀번호 사용 여부 확인
5. Django 콘솔에서 오류 메시지 확인

### Gmail "보안 수준이 낮은 앱의 액세스" 오류
- Gmail에서는 더 이상 이 옵션을 지원하지 않습니다.
- 반드시 **앱 비밀번호**를 사용해야 합니다.

