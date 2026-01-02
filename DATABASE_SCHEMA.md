# MDesk API Server - Database Schema

이 문서는 MDesk API Server의 데이터베이스 스키마를 설명합니다.

---

## 목차

1. [사용자 관리](#1-사용자-관리)
   - [UserProfile](#userprofile)
   - [RustDeskToken](#rustdesktoken)
2. [기기 및 연결](#2-기기-및-연결)
   - [RustDesDevice](#rustdesdevice)
   - [RustDeskPeer](#rustdeskpeer)
   - [RustDeskTag](#rustdesktag)
3. [로그](#3-로그)
   - [ConnLog](#connlog)
   - [FileLog](#filelog)
4. [커스텀 앱 및 상담원](#4-커스텀-앱-및-상담원)
   - [CustomAppConfig](#customappconfig)
   - [SupportAgent](#supportagent)
   - [AgentConnectionLog](#agentconnectionlog)
5. [공유](#5-공유)
   - [ShareLink](#sharelink)
6. [ER 다이어그램](#6-er-다이어그램)

---

## 1. 사용자 관리

### UserProfile

사용자 계정 정보를 저장하는 핵심 테이블입니다.

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK, AUTO |
| `username` | VARCHAR(50) | 사용자명 | UNIQUE, NOT NULL |
| `password` | VARCHAR(128) | 비밀번호 (해시) | NOT NULL |
| `rid` | VARCHAR(16) | MDesk ID | - |
| `uuid` | VARCHAR(60) | UUID | - |
| `autoLogin` | BOOLEAN | 자동 로그인 여부 | DEFAULT: TRUE |
| `rtype` | VARCHAR(20) | 사용자 유형 | - |
| `deviceInfo` | TEXT | 로그인 정보 | - |
| `company_name` | VARCHAR(100) | 회사명 | - |
| `email` | VARCHAR(254) | 이메일 | - |
| `phone` | VARCHAR(20) | 휴대전화 | - |
| `phone_verified` | BOOLEAN | 휴대전화 인증 여부 | DEFAULT: FALSE |
| `company_name` | VARCHAR(100) | 회사명 | |
| `group_id` | INTEGER | 소속 그룹 ID | NULLABLE |
| `membership_level` | VARCHAR(20) | 회원 등급 | DEFAULT: 'free' |
| `membership_start` | DATE | 이용 시작일 | NULLABLE |
| `membership_expires` | DATE | 이용 만료일 | NULLABLE |
| `max_agents` | INTEGER | 최대 상담원 수 | DEFAULT: 3 |
| `is_active` | BOOLEAN | 활성화 여부 | DEFAULT: TRUE |
| `is_admin` | BOOLEAN | 관리자 여부 | DEFAULT: FALSE |
| `last_login` | DATETIME | 마지막 로그인 | NULLABLE |



### RustDeskToken

사용자 인증 토큰을 저장합니다.

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK, AUTO |
| `username` | VARCHAR(20) | 사용자명 | NOT NULL |
| `rid` | VARCHAR(16) | MDesk ID | - |
| `uid` | VARCHAR(16) | 사용자 ID | - |
| `uuid` | VARCHAR(60) | UUID | - |
| `access_token` | VARCHAR(60) | 액세스 토큰 | - |
| `create_time` | DATETIME | 로그인 시간 | AUTO |

**정렬:** `username` 내림차순

---

## 2. 기기 및 연결

### RustDesDevice

등록된 원격 데스크톱 기기 정보를 저장합니다.

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK, AUTO |
| `rid` | VARCHAR(60) | 클라이언트 ID | - |
| `cpu` | VARCHAR(100) | CPU 정보 | NOT NULL |
| `hostname` | VARCHAR(100) | 호스트명 | NOT NULL |
| `memory` | VARCHAR(100) | 메모리 정보 | NOT NULL |
| `os` | VARCHAR(100) | 운영체제 | NOT NULL |
| `uuid` | VARCHAR(100) | UUID | NOT NULL |
| `username` | VARCHAR(100) | 시스템 사용자명 | - |
| `version` | VARCHAR(100) | 클라이언트 버전 | NOT NULL |
| `ip_address` | VARCHAR(60) | IP 주소 | - |
| `create_time` | DATETIME | 기기 등록 시간 | AUTO |
| `update_time` | DATETIME | 기기 업데이트 시간 | AUTO |

**정렬:** `rid` 내림차순

---

### RustDeskPeer

사용자가 저장한 피어(원격 기기) 정보입니다.

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK, AUTO |
| `uid` | VARCHAR(16) | 사용자 ID | NOT NULL |
| `rid` | VARCHAR(60) | 클라이언트 ID | NOT NULL |
| `username` | VARCHAR(20) | 시스템 사용자명 | NOT NULL |
| `hostname` | VARCHAR(30) | 운영체제명 | NOT NULL |
| `alias` | VARCHAR(30) | 별칭 | NOT NULL |
| `platform` | VARCHAR(30) | 플랫폼 | NOT NULL |
| `tags` | VARCHAR(30) | 태그 | NOT NULL |
| `rhash` | VARCHAR(60) | 기기 연결 비밀번호 | NOT NULL |

**정렬:** `username` 내림차순

---

### RustDeskTag

사용자가 생성한 태그 정보입니다.

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK, AUTO |
| `uid` | VARCHAR(16) | 소유 사용자 ID | NOT NULL |
| `tag_name` | VARCHAR(60) | 태그 이름 | NOT NULL |
| `tag_color` | VARCHAR(60) | 태그 색상 | - |

**정렬:** `uid` 내림차순

---

## 3. 로그

### ConnLog

원격 연결 로그를 저장합니다.

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK |
| `action` | VARCHAR(20) | 액션 | NULLABLE |
| `conn_id` | VARCHAR(10) | 연결 ID | NULLABLE |
| `from_ip` | VARCHAR(30) | 접속 IP | NULLABLE |
| `from_id` | VARCHAR(20) | 접속자 ID | NULLABLE |
| `rid` | VARCHAR(20) | 대상 ID | NULLABLE |
| `conn_start` | DATETIME | 연결 시작 시간 | NULLABLE |
| `conn_end` | DATETIME | 연결 종료 시간 | NULLABLE |
| `session_id` | VARCHAR(60) | 세션 ID | NULLABLE |
| `uuid` | VARCHAR(60) | UUID | NULLABLE |

---

### FileLog

파일 전송 로그를 저장합니다.

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK |
| `file` | VARCHAR(500) | 파일 경로 | NOT NULL |
| `remote_id` | VARCHAR(20) | 원격 ID | DEFAULT: '0' |
| `user_id` | VARCHAR(20) | 사용자 ID | DEFAULT: '0' |
| `user_ip` | VARCHAR(20) | 사용자 IP | DEFAULT: '0' |
| `filesize` | VARCHAR(500) | 파일 크기 | DEFAULT: '' |
| `direction` | INTEGER | 전송 방향 | DEFAULT: 0 |
| `logged_at` | DATETIME | 로그 시간 | NULLABLE |


---

## 4. 커스텀 앱 및 상담원

### CustomAppConfig

사용자별 커스텀 앱 설정을 저장합니다.

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK, AUTO |
| `uid_id` | INTEGER | 사용자 FK | FK → UserProfile, UNIQUE |
| `app_name` | VARCHAR(100) | 앱 이름 | DEFAULT: 'MDesk' |
| `logo` | VARCHAR(100) | 로고 파일 경로 | NULLABLE |
| `password` | VARCHAR(100) | 암호 | - |
| `title` | VARCHAR(200) | 제목 | DEFAULT: 'Your Desktop' |
| `description` | VARCHAR(500) | 설명 | DEFAULT: 'Your desktop can be accessed...' |
| `phone` | VARCHAR(20) | 전화번호 | - |
| `url_nickname` | VARCHAR(50) | URL 별명 | UNIQUE, NULLABLE |
| `create_time` | DATETIME | 생성 시간 | AUTO |
| `update_time` | DATETIME | 수정 시간 | AUTO |

**관계:** `uid` → `UserProfile` (1:1)

---

### SupportAgent

고객 지원 상담원 정보를 저장합니다.

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK, AUTO |
| `uid_id` | INTEGER | 사용자 FK | FK → UserProfile |
| `agent_num` | INTEGER | 상담원 번호 | NOT NULL |
| `agent_name` | VARCHAR(100) | 상담원 이름 | NOT NULL |
| `create_time` | DATETIME | 생성 시간 | AUTO |

**복합 유니크:** (`uid`, `agent_num`)  
**정렬:** `agent_num` 오름차순

---

### AgentConnectionLog

상담원의 접속 기록을 저장합니다.

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK, AUTO |
| `uid_id` | INTEGER | 사용자 FK | FK → UserProfile |
| `mdesk_id` | VARCHAR(50) | MDesk ID | NOT NULL |
| `agent_num` | INTEGER | 상담원 번호 | NOT NULL |
| `create_time` | DATETIME | 접속 시간 | AUTO |

**정렬:** `create_time` 내림차순

---

## 5. 공유

### ShareLink

기기 공유 링크를 저장합니다.

| 필드명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK, AUTO |
| `uid` | VARCHAR(16) | 사용자 ID | NOT NULL |
| `shash` | VARCHAR(60) | 링크 Key (해시) | NOT NULL |
| `peers` | VARCHAR(20) | 기기 ID 목록 | NOT NULL |
| `is_used` | BOOLEAN | 사용 여부 | DEFAULT: FALSE |
| `is_expired` | BOOLEAN | 만료 여부 | DEFAULT: FALSE |
| `create_time` | DATETIME | 생성 시간 | AUTO |

**정렬:** `create_time` 내림차순

---

### 5.12 Group (그룹/거래처 정보)

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK, AUTO |
| `uid_id` | INTEGER | 소유자 (FK → UserProfile) | NOT NULL |
| `company_name` | VARCHAR(200) | 회사명 | NOT NULL |
| `business_number` | VARCHAR(20) | 사업자번호 | |
| `representative` | VARCHAR(50) | 대표자명 | |
| `contact_name` | VARCHAR(50) | 담당자 이름 | |
| `contact_phone` | VARCHAR(20) | 담당자 전화번호 | |
| `contact_email` | VARCHAR(254) | 담당자 이메일 | |
| `address` | VARCHAR(300) | 주소 | |
| `address_detail` | VARCHAR(200) | 상세주소 | |
| `memo` | TEXT | 메모 | |
| `is_active` | BOOLEAN | 활성화 여부 | DEFAULT: TRUE |
| `is_deleted` | BOOLEAN | 삭제 여부 (소프트 삭제) | DEFAULT: FALSE |
| `deleted_at` | DATETIME | 삭제 시간 | NULL |
| `create_time` | DATETIME | 생성 시간 | AUTO |
| `update_time` | DATETIME | 수정 시간 | AUTO |

**정렬:** `create_time` 내림차순

---

### 5.13 TeamMember (팀원/직원 정보)

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| `id` | INTEGER | 기본 키 | PK, AUTO |
| `user_id` | INTEGER | 소유자 (FK → UserProfile) | NOT NULL |
| `name` | VARCHAR(50) | 이름 | NOT NULL |
| `phone` | VARCHAR(20) | 전화번호 | |
| `memo` | VARCHAR(200) | 메모 | |
| `is_active` | BOOLEAN | 활성화 여부 | DEFAULT: TRUE |
| `create_time` | DATETIME | 생성 시간 | AUTO |
| `update_time` | DATETIME | 수정 시간 | AUTO |

**정렬:** `name` 오름차순

---

## 6. ER 다이어그램

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MDesk Database Schema                          │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────┐
                    │    UserProfile      │
                    ├─────────────────────┤
                    │ PK id               │
                    │    username         │
                    │    password         │
                    │    rid              │
                    │    membership_level │
                    │    max_agents       │
                    │    ...              │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ CustomAppConfig  │ │  SupportAgent    │ │AgentConnectionLog│
├──────────────────┤ ├──────────────────┤ ├──────────────────┤
│ PK id            │ │ PK id            │ │ PK id            │
│ FK uid_id (1:1)  │ │ FK uid_id        │ │ FK uid_id        │
│    app_name      │ │    agent_num     │ │    mdesk_id      │
│    logo          │ │    agent_name    │ │    agent_num     │
│    url_nickname  │ │    create_time   │ │    create_time   │
│    ...           │ └──────────────────┘ └──────────────────┘
└──────────────────┘


┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  RustDeskToken   │    │   RustDeskPeer   │    │   RustDeskTag    │
├──────────────────┤    ├──────────────────┤    ├──────────────────┤
│ PK id            │    │ PK id            │    │ PK id            │
│    username      │    │    uid           │    │    uid           │
│    rid           │    │    rid           │    │    tag_name      │
│    uid           │    │    hostname      │    │    tag_color     │
│    access_token  │    │    alias         │    └──────────────────┘
│    create_time   │    │    platform      │
└──────────────────┘    │    tags          │
                        │    rhash         │
                        └──────────────────┘


┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  RustDesDevice   │    │     ConnLog      │    │     FileLog      │
├──────────────────┤    ├──────────────────┤    ├──────────────────┤
│ PK id            │    │ PK id            │    │ PK id            │
│    rid           │    │    action        │    │    file          │
│    cpu           │    │    conn_id       │    │    remote_id     │
│    hostname      │    │    from_ip       │    │    user_id       │
│    memory        │    │    from_id       │    │    user_ip       │
│    os            │    │    rid           │    │    filesize      │
│    uuid          │    │    conn_start    │    │    direction     │
│    version       │    │    conn_end      │    │    logged_at     │
│    ip_address    │    │    session_id    │    └──────────────────┘
│    create_time   │    │    uuid          │
│    update_time   │    └──────────────────┘
└──────────────────┘

┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│    ShareLink     │    │      Group       │    │   TeamMember     │
├──────────────────┤    ├──────────────────┤    ├──────────────────┤
│ PK id            │    │ PK id            │    │ PK id            │
│    uid           │    │ FK uid_id        │    │ FK user_id       │
│    shash         │    │    company_name  │    │    name          │
│    peers         │    │    business_num  │    │    phone         │
│    is_used       │    │    contact_name  │    │    memo          │
│    is_expired    │    │    is_deleted    │    │    is_active     │
│    create_time   │    │    create_time   │    │    create_time   │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

---

## 테이블 요약

| 테이블명 | 설명 | 레코드 타입 |
|----------|------|------------|
| `api_userprofile` | 사용자 계정 | 마스터 |
| `api_rustdesktoken` | 인증 토큰 | 트랜잭션 |
| `api_rustdesdevice` | 등록 기기 | 마스터 |
| `api_rustdeskpeer` | 피어 정보 | 마스터 |
| `api_rustdesktag` | 태그 | 마스터 |
| `api_connlog` | 연결 로그 | 로그 |
| `api_filelog` | 파일 전송 로그 | 로그 |
| `api_customappconfig` | 커스텀 앱 설정 | 설정 |
| `api_supportagent` | 상담원 | 마스터 |
| `api_agentconnectionlog` | 상담원 접속 로그 | 로그 |
| `api_sharelink` | 공유 링크 | 트랜잭션 |
| `api_group` | 그룹 (거래처) | 마스터 |
| `api_teammember` | 팀원 (직원) | 마스터 |

---

## 인덱스

Django ORM이 자동으로 생성하는 기본 인덱스:

- 모든 테이블의 `id` (Primary Key)
- `UserProfile.username` (UNIQUE)
- `CustomAppConfig.uid_id` (UNIQUE)
- `CustomAppConfig.url_nickname` (UNIQUE)
- `SupportAgent.(uid_id, agent_num)` (복합 UNIQUE)

---

*문서 생성일: 2024*  
*최종 수정일: 2026-01-01*  
*MDesk API Server v1.0*

