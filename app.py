import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory, redirect, url_for
from flask_cors import CORS
from bson.objectid import ObjectId
from openai import OpenAI
from werkzeug.utils import secure_filename
from banco import db, conectar_banco

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuração da API NVIDIA / OpenAI
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
ai_client = (
    OpenAI(
        base_url="https://integrate.api.nvidia.com/v1", api_key=NVIDIA_API_KEY
    )
    if NVIDIA_API_KEY
    else None
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Caminhos locais para o Obsidian
CAMINHO_VAULT_OBSIDIAN = os.getenv(
    "CAMINHO_OBSIDIAN",
    r"C:\Users\Thales Biondi\Desktop\segundo_cerebro_catolico\cerebro_catolico\Estudos"
)
PASTA_TEMPLATES = os.getenv(
    "PASTA_TEMPLATES",
    r"C:\Users\Thales Biondi\Desktop\segundo_cerebro_catolico\cerebro_catolico\Templates"
)

colecao = conectar_banco()


def serializar_estudo(estudo):
    """Converte campos do MongoDB para tipos seguros em JSON."""
    estudo = dict(estudo)
    estudo["_id"] = str(estudo["_id"])

    data_criacao = estudo.get("data_criacao")
    if isinstance(data_criacao, datetime):
        estudo["data_criacao"] = data_criacao.isoformat()

    return estudo


def criar_nota_com_template(estudo, nome_template, arquivos_anexados):
    """Gera o arquivo Markdown do Obsidian localmente se a pasta existir."""
    if not os.path.exists(CAMINHO_VAULT_OBSIDIAN):
        return

    caminho_template = os.path.join(PASTA_TEMPLATES, nome_template) if nome_template else ""
    if os.path.exists(caminho_template):
        with open(caminho_template, "r", encoding="utf-8") as f:
            conteudo_template = f.read()
    else:
        conteudo_template = "# {{TITULO}}\n\n## 📖 O que é?\n{{RESUMO}}\n\n## ✝️ Conteúdo\n{{CONTEUDO}}\n\n## 📎 Anexos\n{{ANEXOS}}\n\n## 📚 Referências\n{{REFERENCIAS}}\n\n## 🔗 Relacionados\n{{RELACIONADOS}}\n\n## 🏷️ Tags\n{{TAGS}}"

    tags_fmt = " ".join([f"#{t}" for t in estudo.get("tags", [])])
    refs_fmt = "\n".join([f"- {r}" for r in estudo.get("referencias", [])])
    rel_fmt = "\n".join([f"- [[{r}]]" for r in estudo.get("relacionados", [])])
    anexos_fmt = (
        "\n".join([f"- [{a['nome']}](file:///{a['caminho']})" for a in arquivos_anexados])
        or "Nenhum arquivo anexado."
    )

    conteudo_final = (
        conteudo_template.replace("{{TITULO}}", estudo.get("titulo", ""))
        .replace("{{RESUMO}}", estudo.get("resumo", ""))
        .replace("{{CONTEUDO}}", estudo.get("conteudo", ""))
        .replace("{{ANEXOS}}", anexos_fmt)
        .replace("{{REFERENCIAS}}", refs_fmt)
        .replace("{{RELACIONADOS}}", rel_fmt)
        .replace("{{TAGS}}", tags_fmt)
    )

    pasta_destino = os.path.join(
        CAMINHO_VAULT_OBSIDIAN, estudo.get("categoria", "Conceitos")
    )
    os.makedirs(pasta_destino, exist_ok=True)
    with open(
        os.path.join(pasta_destino, f"{estudo['titulo']}.md"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(conteudo_final)


@app.route('/')
def index():
    # Busca todas as notas cadastradas para renderizar no HTML
    notas = list(colecao.find().sort("data_criacao", -1))
    return render_template('index.html', notas=notas)


@app.route("/pregacao")
def pregacao():
    return render_template("pregacao.html")


@app.route("/api/templates", methods=["GET"])
def listar_templates():
    if not os.path.exists(PASTA_TEMPLATES):
        return jsonify({"templates": []}), 200
    return jsonify({
        "templates": [f for f in os.listdir(PASTA_TEMPLATES) if f.endswith(".md")]
    }), 200


@app.route("/api/estudos", methods=["POST"])
def cadastrar_estudo():
    try:
        titulo = request.form.get("titulo")
        categoria = request.form.get("categoria", "Conceitos")
        resumo = request.form.get("resumo", "")
        conteudo = request.form.get("conteudo", "")
        template_usado = request.form.get("template", "")

        referencias = [r.strip() for r in request.form.get("referencias", "").split(",") if r.strip()]
        relacionados = [r.strip() for r in request.form.get("relacionados", "").split(",") if r.strip()]
        tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]

        if not titulo:
            return jsonify({"erro": "O campo 'Título' é obrigatório."}), 400

        arquivos_salvos = []
        for file in request.files.getlist("arquivos"):
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                caminho = os.path.join(UPLOADS_DIR, filename)
                file.save(caminho)
                arquivos_salvos.append({
                    "nome": filename,
                    "caminho": caminho.replace("\\", "/"),
                    "url": f"/uploads/{filename}",
                })

        doc = {
            "titulo": titulo,
            "categoria": categoria,
            "resumo": resumo,
            "conteudo": conteudo,
            "referencias": referencias,
            "relacionados": relacionados,
            "tags": tags,
            "arquivos": arquivos_salvos,
            "template_usado": template_usado,
            "origem": "Web",
            "data_criacao": datetime.utcnow()
        }

        colecao.insert_one(doc)

        try:
            criar_nota_com_template(doc, template_usado, arquivos_salvos)
        except Exception:
            pass

        return redirect(url_for('index'))

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/api/estudos", methods=["GET"])
def listar_estudos():
    try:
        estudos = [serializar_estudo(est) for est in colecao.find().sort("data_criacao", -1)]
        return jsonify({"estudos": estudos}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/api/estudos/<estudo_id>", methods=["GET"])
def obter_estudo(estudo_id):
    """Busca os dados de uma nota específica pelo ID para carregar no Modal de Edição."""
    try:
        if not ObjectId.is_valid(estudo_id):
            return jsonify({"erro": "ID inválido"}), 400

        estudo = colecao.find_one({"_id": ObjectId(estudo_id)})
        if not estudo:
            return jsonify({"erro": "Estudo não encontrado"}), 404

        return jsonify({
            "id": str(estudo["_id"]),
            "titulo": estudo.get("titulo", ""),
            "categoria": estudo.get("categoria", "Conceitos"),
            "resumo": estudo.get("resumo", ""),
            "conteudo": estudo.get("conteudo", ""),
            "tags": ", ".join(estudo.get("tags", [])),
            "referencias": ", ".join(estudo.get("referencias", []))
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/api/estudos/<estudo_id>/editar", methods=["POST"])
def editar_estudo(estudo_id):
    """Atualiza a nota no MongoDB e no Obsidian."""
    try:
        if not ObjectId.is_valid(estudo_id):
            return jsonify({"erro": "ID inválido"}), 400

        titulo = request.form.get("titulo")
        categoria = request.form.get("categoria", "Conceitos")
        resumo = request.form.get("resumo", "")
        conteudo = request.form.get("conteudo", "")
        tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
        referencias = [r.strip() for r in request.form.get("referencias", "").split(",") if r.strip()]

        colecao.update_one(
            {"_id": ObjectId(estudo_id)},
            {
                "$set": {
                    "titulo": titulo,
                    "categoria": categoria,
                    "resumo": resumo,
                    "conteudo": conteudo,
                    "tags": tags,
                    "referencias": referencias
                }
            }
        )

        if os.path.exists(CAMINHO_VAULT_OBSIDIAN):
            pasta_destino = os.path.join(CAMINHO_VAULT_OBSIDIAN, categoria)
            os.makedirs(pasta_destino, exist_ok=True)
            caminho_arquivo = os.path.join(pasta_destino, f"{titulo}.md")
            
            tags_fmt = " ".join([f"#{t}" for t in tags])
            refs_fmt = "\n".join([f"- {r}" for r in referencias])
            conteudo_md = f"# {titulo}\n\n## 📖 O que é?\n{resumo}\n\n## ✝️ Conteúdo\n{conteudo}\n\n## 📚 Referências\n{refs_fmt}\n\n## 🏷️ Tags\n{tags_fmt}"
            
            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                f.write(conteudo_md)

        return redirect(url_for('index'))

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/api/gerar-pregacao", methods=["POST"])
def gerar_pregacao_ia():
    if not ai_client:
        return jsonify({"erro": "Chave NVIDIA_API_KEY não configurada no servidor."}), 400

    dados = request.get_json() or {}
    tema = dados.get("tema", "").strip()
    publico = dados.get("publico", "Geral")
    notas_base = dados.get("notas", [])

    if not tema:
        return jsonify({"erro": "Informe o tema da pregação."}), 400

    prompt = f"""
Você é um assistente teológico católico especialista em homilética, catequese e oratória sagrada.
Gere uma estrutura clara e profunda para uma Pregação / Catequese baseada nas seguintes diretrizes:

- Tema Principal: {tema}
- Público-Alvo: {publico}
- Estudos/Notas Teológicas de Apoio:
{chr(10).join(['- ' + str(n) for n in notas_base])}

Estruture a resposta no seguinte formato Markdown:
1. 🎯 Ofertório / Objetivo Central (O que a assembleia deve guardar no coração)
2. 📖 Leitura Bíblica & Fundamentação do Magistério (CIC / Padres da Igreja)
3. 💡 Introdução / Gancho Homilético (Como prender a atenção)
4. 📌 Pontos de Desenvolvimento (3 a 4 pontos teológicos e práticos)
5. 🕊️ Aplicação Pastoral e Oração Final
"""

    try:
        completion = ai_client.chat.completions.create(
            model=os.getenv("NVIDIA_MODEL", "meta/muse-glimmer-30b"),
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            top_p=0.95,
            max_tokens=8192,
            stream=False,
        )
        roteiro = completion.choices[0].message.content
        return jsonify({"roteiro": roteiro}), 200
    except Exception as e:
        app.logger.exception("Erro ao gerar pregação com IA")
        return jsonify({
            "erro": "Não foi possível gerar a pregação agora. Verifique a chave NVIDIA_API_KEY, o modelo configurado e a conexão com a API.",
            "detalhe": str(e),
        }), 502


@app.route("/uploads/<filename>")
def servir_arquivo(filename):
    return send_from_directory(UPLOADS_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
