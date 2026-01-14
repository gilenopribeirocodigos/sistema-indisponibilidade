import bcrypt
from datetime import datetime, timedelta
from typing import Optional

def verificar_senha(senha_digitada: str, senha_hash: str) -> bool:
    """
    Verifica se a senha digitada confere com o hash armazenado.
    """
    return bcrypt.checkpw(
        senha_digitada.encode('utf-8'), 
        senha_hash.encode('utf-8')
    )

def criar_hash_senha(senha: str) -> str:
    """
    Cria hash bcrypt de uma senha.
    Útil para criar novos usuários.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(senha.encode('utf-8'), salt).decode('utf-8')

# Exemplo de uso:
# senha_admin = "admin123"
# hash_gerado = criar_hash_senha(senha_admin)
# print(hash_gerado)