"""DroneVision: envia fotos de drone ao Azure AI Vision e mostra descrição e tags."""

from __future__ import annotations

import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, render_template, request

# Limite do Analyze Image v3.2: imagem de até 4 MB.
LIMITE_BYTES = 4 * 1024 * 1024

app = Flask(__name__)
# Folga para o overhead do multipart; o limite de 4 MB da imagem é checado abaixo.
app.config["MAX_CONTENT_LENGTH"] = LIMITE_BYTES + 1024 * 1024

ASSINATURAS = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"BM": "image/bmp",
}


class ErroAnalise(Exception):
    """Erro com mensagem pronta para o operador e o status HTTP a devolver."""

    def __init__(self, mensagem: str, status: int = 502) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def tipo_da_imagem(dados: bytes) -> str | None:
    """Identifica o formato pelos primeiros bytes, sem confiar na extensão."""
    for assinatura, tipo in ASSINATURAS.items():
        if dados.startswith(assinatura):
            return tipo
    return None


def analisar_imagem(dados: bytes) -> tuple[str, float | None, list[dict]]:
    endpoint = os.environ.get("AZURE_VISION_ENDPOINT", "").strip().rstrip("/")
    chave = os.environ.get("AZURE_VISION_KEY", "").strip()
    if not endpoint or not chave:
        raise ErroAnalise(
            "O serviço de visão computacional não está configurado nesta aplicação.",
            503,
        )

    parametros = urlencode(
        {"visualFeatures": "Tags,Description", "language": "pt"}
    )
    requisicao = Request(
        f"{endpoint}/vision/v3.2/analyze?{parametros}",
        data=dados,
        headers={
            "Ocp-Apim-Subscription-Key": chave,
            "Content-Type": "application/octet-stream",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(requisicao, timeout=60) as resposta:
            resultado = json.loads(resposta.read().decode("utf-8"))
    except HTTPError as erro:
        if erro.code == 400:
            raise ErroAnalise(
                "O Azure AI Vision recusou a imagem. Use JPEG, PNG, GIF ou BMP, "
                "com lado entre 50 e 16000 pixels.",
                400,
            ) from erro
        if erro.code in (401, 403):
            raise ErroAnalise(
                "A aplicação não conseguiu se autenticar no Azure AI Vision "
                "(chave ou endpoint inválidos).",
                502,
            ) from erro
        if erro.code == 429:
            raise ErroAnalise(
                "O limite de requisições do Azure AI Vision foi atingido. "
                "Tente novamente em alguns instantes.",
                503,
            ) from erro
        raise ErroAnalise(
            f"O Azure AI Vision respondeu com erro (HTTP {erro.code}). "
            "Tente novamente mais tarde.",
            503,
        ) from erro
    except (URLError, TimeoutError, OSError) as erro:
        raise ErroAnalise(
            "O Azure AI Vision está indisponível ou não respondeu a tempo. "
            "Tente novamente mais tarde.",
            503,
        ) from erro
    except json.JSONDecodeError as erro:
        raise ErroAnalise(
            "O Azure AI Vision retornou uma resposta inválida.", 502
        ) from erro

    legendas = resultado.get("description", {}).get("captions", [])
    if not legendas or not legendas[0].get("text"):
        raise ErroAnalise(
            "A análise terminou, mas o serviço não gerou uma descrição para esta imagem.",
            502,
        )

    tags = [t for t in resultado.get("tags", []) if t.get("name")]
    return legendas[0]["text"], legendas[0].get("confidence"), tags


def pagina(status: int = 200, **contexto):
    return render_template("index.html", **contexto), status


@app.get("/")
def index():
    return pagina()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analisar")
def analisar():
    arquivo = request.files.get("imagem")
    if arquivo is None or not arquivo.filename:
        return pagina(400, erro="Selecione uma imagem antes de enviar.")

    dados = arquivo.read()
    if not dados:
        return pagina(400, erro="O arquivo enviado está vazio.")
    if len(dados) > LIMITE_BYTES:
        return pagina(400, erro="A imagem excede o limite de 4 MB.")

    tipo = tipo_da_imagem(dados)
    if tipo is None:
        return pagina(
            400,
            erro="Arquivo inválido: envie uma imagem JPEG, PNG, GIF ou BMP.",
        )

    previa = f"data:{tipo};base64,{base64.b64encode(dados).decode('ascii')}"
    try:
        descricao, confianca, tags = analisar_imagem(dados)
    except ErroAnalise as erro:
        return pagina(erro.status, erro=erro.mensagem, previa=previa)

    return pagina(
        descricao=descricao,
        confianca=confianca,
        tags=tags,
        previa=previa,
        nome=arquivo.filename,
    )


@app.errorhandler(413)
def arquivo_grande(_erro):
    return pagina(413, erro="A imagem excede o limite de 4 MB.")


if __name__ == "__main__":
    app.run(debug=True)
