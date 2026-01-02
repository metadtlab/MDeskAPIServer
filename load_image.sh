#!/bin/bash

IMAGE_NAME="rustdesk-api-server"
TAG="latest"
TAR_FILE="rustdesk_image.tar"

echo "=========================================="
echo "[1/2] 도커 이미지 로드 중: $TAR_FILE"
echo "=========================================="
if [ -f "$TAR_FILE" ]; then
    docker load -i $TAR_FILE
else
    echo "[오류] $TAR_FILE 파일이 존재하지 않습니다."
    exit 1
fi

echo ""
echo "=========================================="
echo "[2/2] 컨테이너 실행 중 (docker-compose)"
echo "=========================================="
# 이미지 빌드를 생략하고 로드된 이미지를 사용하도록 실행
docker-compose up -d

echo ""
echo "=========================================="
echo "배포 완료!"
docker ps | grep $IMAGE_NAME
echo "=========================================="


