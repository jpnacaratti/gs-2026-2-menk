#!/usr/bin/env bash
set -euo pipefail

RM="rm94112"
PROJETO="dronevision"
LOCALIZACAO="${LOCALIZACAO:-brazilsouth}"
SKU_VISION="${SKU_VISION:-S1}"
SKU_PLANO="${SKU_PLANO:-B1}"
RUNTIME="PYTHON:3.12"

RG="rg-${PROJETO}-${RM}"
VISION="aiv-${PROJETO}-${RM}"
PLANO="plan-${PROJETO}-${RM}"
WEBAPP="app-${PROJETO}-${RM}"

cd "$(dirname "$0")"

echo ">> Registrando provedores de recursos"
az provider register --namespace Microsoft.CognitiveServices --wait
az provider register --namespace Microsoft.Web --wait

echo ">> Resource Group: ${RG}"
az group create --name "$RG" --location "$LOCALIZACAO" --output none

echo ">> Azure AI Vision: ${VISION}"
if ! az cognitiveservices account show --name "$VISION" --resource-group "$RG" --output none 2>/dev/null; then
  az cognitiveservices account create \
    --name "$VISION" \
    --resource-group "$RG" \
    --kind ComputerVision \
    --sku "$SKU_VISION" \
    --location "$LOCALIZACAO" \
    --custom-domain "$VISION" \
    --yes \
    --output none
fi

VISION_ENDPOINT=$(az cognitiveservices account show \
  --name "$VISION" --resource-group "$RG" \
  --query properties.endpoint --output tsv)
VISION_KEY=$(az cognitiveservices account keys list \
  --name "$VISION" --resource-group "$RG" \
  --query key1 --output tsv)

echo ">> App Service Plan: ${PLANO}"
if ! az appservice plan show --name "$PLANO" --resource-group "$RG" --output none 2>/dev/null; then
  az appservice plan create \
    --name "$PLANO" \
    --resource-group "$RG" \
    --location "$LOCALIZACAO" \
    --sku "$SKU_PLANO" \
    --is-linux \
    --output none
fi

echo ">> Web App: ${WEBAPP}"
if ! az webapp show --name "$WEBAPP" --resource-group "$RG" --output none 2>/dev/null; then
  az webapp create \
    --name "$WEBAPP" \
    --resource-group "$RG" \
    --plan "$PLANO" \
    --runtime "$RUNTIME" \
    --output none
fi

echo ">> Configurando variáveis de ambiente e comando de inicialização"
az webapp config appsettings set \
  --name "$WEBAPP" \
  --resource-group "$RG" \
  --settings \
    AZURE_VISION_ENDPOINT="$VISION_ENDPOINT" \
    AZURE_VISION_KEY="$VISION_KEY" \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  --output none

az webapp config set \
  --name "$WEBAPP" \
  --resource-group "$RG" \
  --startup-file "gunicorn --bind=0.0.0.0 --timeout 120 app:app" \
  --output none

echo ">> Deploy (zip) via Azure CLI"
rm -f app.zip
python3 - <<'PY'
import zipfile
with zipfile.ZipFile("app.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for arq in ("app.py", "requirements.txt", "templates/index.html"):
        z.write(arq)
PY
az webapp deploy \
  --name "$WEBAPP" \
  --resource-group "$RG" \
  --src-path app.zip \
  --type zip \
  --output none
rm -f app.zip

echo
echo "Implantação concluída."
echo "Aplicação: https://${WEBAPP}.azurewebsites.net"
