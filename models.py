from sqlalchemy import Column, Integer, String, Boolean, Date, Text, ForeignKey, TIMESTAMP, DateTime
from sqlalchemy.sql import func
from database import Base

# ============================================
# CLASSE 1: EstruturaEquipes
# Representa a tabela ESTRUTURA_EQUIPES
# ============================================
class EstruturaEquipes(Base):
    __tablename__ = 'estrutura_equipes'
    
    id = Column(Integer, primary_key=True, index=True)
    regional = Column(String)
    polo = Column(String)
    base = Column(String)
    prefixo = Column(String, index=True)
    matricula = Column(String, index=True)
    colaborador = Column(String, index=True)
    descr_secao = Column(String)
    descr_situacao = Column(String)
    placas = Column(String)
    tipo_equipe = Column(String)
    processo_equipe = Column(String)
    superv_campo = Column(String)
    superv_operacao = Column(String)
    coordenador = Column(String)


# ============================================
# CLASSE 2: Usuario
# Representa a tabela USUARIOS
# ============================================
class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    login = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    perfil = Column(String, nullable=False)  # 'ADMIN', 'SUPERVISOR', 'FISCAL'
    base_responsavel = Column(String)
    ativo = Column(Boolean, default=True)


# ============================================
# CLASSE 3: MotivoIndisponibilidade
# Representa a tabela MOTIVOS_INDISPONIBILIDADE
# ============================================
class MotivoIndisponibilidade(Base):
    __tablename__ = 'motivos_indisponibilidade'
    
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, unique=True, nullable=False)
    ativo = Column(Boolean, default=True)


# ============================================
# CLASSE 4: Indisponibilidade (ATUALIZADA)
# Representa a tabela INDISPONIBILIDADES
# ============================================
class Indisponibilidade(Base):
    __tablename__ = 'indisponibilidades'
    
    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    eletricista_id = Column(Integer, ForeignKey('estrutura_equipes.id'))
    eletricista2_id = Column(Integer, ForeignKey('estrutura_equipes.id'))  # ← NOVO!
    matricula = Column(String)
    prefixo = Column(String, nullable=False)
    motivo_id = Column(Integer, ForeignKey('motivos_indisponibilidade.id'))
    observacao = Column(Text)
    usuario_registro = Column(Integer, ForeignKey('usuarios.id'))
    criado_em = Column(TIMESTAMP, server_default=func.now())
    # Campo 'tipo' foi REMOVIDO (estava obsoleto)


# ============================================
# CLASSE 5: EquipeDia (NOVA)
# Controle de frequência - equipes montadas por dia
# ============================================
class EquipeDia(Base):
    __tablename__ = "equipes_dia"
    
    id = Column(Integer, primary_key=True, index=True)
    eletricista_id = Column(Integer, ForeignKey("estrutura_equipes.id"), nullable=False)
    prefixo = Column(String, nullable=False)
    data = Column(Date, nullable=False)
    supervisor_registro = Column(String, nullable=False)
    criado_em = Column(DateTime, server_default=func.now())
    observacoes = Column(Text)


# ============================================
# CLASSE 6: Remanejamento (NOVA)
# Remanejamentos temporários de eletricistas
# ============================================
class Remanejamento(Base):
    __tablename__ = "remanejamentos"
    
    id = Column(Integer, primary_key=True, index=True)
    eletricista_id = Column(Integer, ForeignKey("estrutura_equipes.id"), nullable=False)
    supervisor_origem = Column(String, nullable=False)
    supervisor_destino = Column(String, nullable=False)    
    data_remanejamento = Column(Date, nullable=False)
    temporario = Column(Boolean, default=True)
    usuario_registro = Column(Integer, ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, server_default=func.now())

    observacoes = Column(Text)

# Função para criar todas as tabelas
def criar_tabelas():
    """Cria todas as tabelas no banco de dados"""
    from database import engine
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas com sucesso!")

