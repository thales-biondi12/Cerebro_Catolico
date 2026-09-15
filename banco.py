import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Carrega as variáveis do arquivo .env
load_dotenv()


def conectar_banco():
    # Lê a URL do MongoDB a partir do .env ou usa o servidor local como fallback
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)

    # Nome do seu banco de dados
    db = client["segundo_cerebro_catolico"]
    return db["estudos"]