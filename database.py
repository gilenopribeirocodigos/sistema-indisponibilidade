from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Carrega variáveis do arquivo .env
load_dotenv()

# Pega a connection string do .env
DATABASE_URL = os.getenv('DATABASE_URL')

# Cria o motor de conexão com o banco
engine = create_engine(DATABASE_URL)

# Cria a fábrica de sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria a base para os models
Base = declarative_base()

# Função para obter sessão do banco
def get_db():
    """
    Função que retorna uma sessão do banco.
    Uso: db = next(get_db())
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        