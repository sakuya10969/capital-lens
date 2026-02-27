#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

IMAGE="cldev.azurecr.io/capital-lens:latest"
ACR_NAME="cldev"
APP_NAME="ca-cl-dev-010"
RESOURCE_GROUP="rg-cl-dev-010"

REVISION_SUFFIX="rev-$(date +%y-%m%d-%H%M)"

echo "  Capital Lens - Deploy"
echo "Image:    $IMAGE"
echo "Revision: $REVISION_SUFFIX"

# 1. Azure ログイン
echo "[1/5] Azure にログイン中..."
az login

# 2. ACR ログイン
echo "[2/5] ACR ($ACR_NAME) にログイン中..."
az acr login --name "$ACR_NAME"

# 3. Docker ビルド
echo "[3/5] Docker イメージをビルド中..."
docker build --no-cache --pull -t "$IMAGE" -f "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR"

# 4. Docker プッシュ
echo "[4/5] イメージを ACR にプッシュ中..."
docker push "$IMAGE"

# 5. Container Apps 更新
echo "[5/5] Container Apps を更新中..."
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$IMAGE" \
  --revision-suffix "$REVISION_SUFFIX"

echo "  デプロイ完了"
echo "  Revision: $REVISION_SUFFIX"
