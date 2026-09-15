import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Obtém a URI do ambiente
MONGO_URI = os.getenv("MONGO_URI")

# Conecta ao cluster
client = MongoClient(MONGO_URI)

# Define o banco de dados (A variável 'db' precisa ter exatamente este nome)
db = client["segundo_cerebro"]  # Altere para o nome exato do seu banco no Atlas