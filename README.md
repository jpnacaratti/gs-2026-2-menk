# DroneVision

MVP de apoio à análise de imagens de drone. O operador envia uma fotografia pela página web e recebe uma descrição em português e as etiquetas identificadas, geradas pelo **Azure AI Vision**. A aplicação roda no **Azure App Service**.

## Recursos criados (RM 94112)

| Recurso | Nome |
|---|---|
| Resource Group | `rg-dronevision-rm94112` |
| Azure AI Vision | `aiv-dronevision-rm94112` |
| App Service Plan | `plan-dronevision-rm94112` |
| Web App | `app-dronevision-rm94112` |

## Implantação (Azure Cloud Shell, Bash)

```bash
git clone <URL-DO-REPOSITORIO>
cd <PASTA-DO-REPOSITORIO>
bash implantar-rm94112.sh
```

O script cria tudo pela Azure CLI, configura as variáveis, e publica o código com `az webapp deploy`. Ao final imprime `https://app-dronevision-rm94112.azurewebsites.net`.

## Configuração

As variáveis ficam no topo do `implantar-rm94112.sh` (RM, nome do projeto, região, SKUs e runtime). Os nomes dos recursos são montados a partir delas, então basta editar ali uma vez para valer no script inteiro, sem trocar valores em vários lugares.

`LOCALIZACAO` (padrão `brazilsouth`), `SKU_VISION` (padrão `S1`; use `F0` se não houver outro F0 na assinatura) e `SKU_PLANO` (padrão `B1`) também podem ser passadas ao rodar, por exemplo `SKU_VISION=F0 bash implantar-rm94112.sh`.
