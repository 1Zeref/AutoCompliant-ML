#!/usr/bin/env bash
set -e

echo "================================================================"
echo "          VIETNAM MOTORBIKE SMART TRAFFIC ASSISTANT"
echo "          Khoi dong Ung dung Toan trinh (Docker 1-Click)"
echo "================================================================"
echo ""

if ! docker info > /dev/null 2>&1; then
    echo "[LOI] Docker chua duoc bat hoac chua duoc cai dat!"
    echo "Vui long khoi dong Docker Engine va thu lai."
    exit 1
fi

echo "[OK] Docker Engine da san sang."

if [ ! -f .env ] && [ -f .env.example ]; then
    echo "[INFO] Dang tao .env tu .env.example..."
    cp .env.example .env
    RANDOM_KEY=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
    sed -i.bak "s|SECRET_KEY=.*|SECRET_KEY=${RANDOM_KEY}|g" .env && rm -f .env.bak
    echo "[OK] Da tao .env mac dinh kem SECRET_KEY ngau nhien."
fi

case "$1" in
    stop)
        echo "[INFO] Dang dung he thong..."
        docker compose down
        exit 0
        ;;
    logs)
        docker compose logs -f
        exit 0
        ;;
    restart)
        docker compose restart
        exit 0
        ;;
    clean)
        echo "[CANH BAO] Don dep toan bo containers va images..."
        docker compose down -v --rmi local
        exit 0
        ;;
esac

echo "[INFO] Dang build va khoi dong he thong..."
docker compose up -d --build

echo "[INFO] Dang kiem tra trang thai san sang cua he thong..."
ATTEMPTS=0
while [ $ATTEMPTS -lt 15 ]; do
    if docker compose ps | grep -q "healthy"; then
        break
    fi
    sleep 2
    ATTEMPTS=$((ATTEMPTS+1))
done

echo ""
echo "================================================================"
echo "          HE THONG TRAFFIC ASSISTANT DA KHOI DONG THANH CONG!"
echo "================================================================"
echo "  🌐 Giao dien PWA & HUD:  http://localhost:8000"
echo "  🧠 Trang Quan Tri AI:    http://localhost:8000/training.html"
echo "  🔌 Swagger API Docs:     http://localhost:8000/docs"
echo "  📊 Health Check API:     http://localhost:8000/api/v1/health"
echo "================================================================"
