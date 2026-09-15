import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("A variável de ambiente MONGO_URI não foi configurada.")

client = MongoClient(MONGO_URI)

# Altere "segundo_cerebro" para o nome exato do seu banco no MongoDB Atlas se necessário
db = client["segundo_cerebro"] 

def conectar_banco():
    """Retorna a coleção principal de estudos."""
    return db["estudos"]