import os
import glob
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Conexão com o MongoDB Atlas usando a sua MONGO_URI
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

# Altere para o nome exato do seu banco e da sua coleção no MongoDB
db = client["segundo_cerebro"]  # Exemplo: nome do seu banco
colecao = db["estudos"]         # Exemplo: nome da sua coleção de notas

# CAMINHO DA SUA PASTA DO OBSIDIAN
# Subsitua pelo caminho completo da sua pasta do Obsidian no seu PC
PASTA_OBSIDIAN = r"C:\Users\Thales Biondi\Desktop\segundo_cerebro_catolico\cerebro_catolico"

def importar_notas():
    # Busca todos os arquivos .md dentro da pasta (e subpastas)
    padrao_busca = os.path.join(PASTA_OBSIDIAN, "**", "*.md")
    arquivos_md = glob.glob(padrao_busca, recursive=True)
    
    print(f"Encontrados {len(arquivos_md)} arquivos .md no Obsidian.\n")
    
    notas_inseridas = 0
    for caminho_arquivo in arquivos_md:
        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                conteudo = f.read()
            
            # Pega o nome do arquivo (sem o .md) para usar como título
            nome_arquivo = os.path.basename(caminho_arquivo)
            titulo = os.path.splitext(nome_arquivo)[0]
            
            # Estrutura do documento que será salvo no MongoDB
            documento = {
                "titulo": titulo,
                "conteudo": conteudo,
                "origem": "Obsidian Import",
                "data_criacao": datetime.utcnow()
            }
            
            # Insere no banco (evita duplicar se já existir uma nota com o mesmo título)
            colecao.update_one(
                {"titulo": titulo},
                {"$set": documento},
                upsert=True
            )
            
            print(f"✓ Importado/Atualizado: {titulo}")
            notas_inseridas += 1
            
        except Exception as e:
            print(f"✕ Erro ao ler {caminho_arquivo}: {e}")

    print(f"\nFinalizado! Total de {notas_inseridas} notas sincronizadas com o MongoDB Atlas.")

if __name__ == "__main__":
    importar_notas()