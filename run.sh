#!/bin/bash

# 리눅스 줄바꿈(LF) 준수 여부 확인 필요
cd /rustdesk-api-server

# 만약 PostgreSQL을 사용한다면 아래 SQLite 초기화 코드는 무시됩니다.
if [ "$DATABASE_TYPE" = "SQLITE" ] || [ -z "$DATABASE_TYPE" ]; then
    if [ ! -e "./db/db.sqlite3" ]; then
        if [ -e "./db_bak/db.sqlite3" ]; then
            cp "./db_bak/db.sqlite3" "./db/db.sqlite3"
            echo "Initializing SQLite database..."
        fi
    fi
fi

python manage.py makemigrations
python manage.py migrate
python manage.py runserver ${HOST:-0.0.0.0}:21114
