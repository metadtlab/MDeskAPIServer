FROM python:3.10.3-alpine

WORKDIR /rustdesk-api-server
ADD . /rustdesk-api-server

# 설치 시스템 라이브러리 (Pillow 및 DB 연결용)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    mariadb-connector-c-dev \
    postgresql-dev \
    pkgconfig \
    zlib-dev \
    jpeg-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev \
    harfbuzz-dev \
    fribidi-dev

# 패키지 설치 및 초기화 준비
RUN set -ex \
    && pip install --no-cache-dir --disable-pip-version-check -r requirements.txt \
    && rm -rf /var/cache/apk/* \
    && cp -r ./db ./db_bak

ENV HOST="0.0.0.0"
ENV TZ="Asia/Seoul"

EXPOSE 80/tcp
EXPOSE 80/udp

# run.sh 대신 직접 명령어를 사용합니다. (줄바꿈 에러 방지)
CMD ["sh", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:80"]