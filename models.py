from sqlalchemy import Column, Integer, String, Boolean, Date, Text, ForeignKey, TIMESTAMP, DateTime
from sqlalchemy.sql import func
from database import Base
from datetime import datetime

# ============================================
# CLASSE: EstruturaEquipes (PRINCIPAL)
# Representa a tabela de eletricistas
# ============================================
class EstruturaEquipes(Base):
    __tablename__ = "estrutura_equipes"
    
    id = Column(Integer, primary_key=True, index=True)
    regional = Column(String(100))
    polo = Column(String(100))
    base = Column(String(100))
    prefixo = Column(String(50))
    matricula = Column(String(20))
    colaborador = Column(String(200))
    descr_secao = Column(String(100))
    descr_situacao = Column(String(50))
    placas = Column(String(100))
    tipo_equipe = Column(String(100))
    processo_equipe = Column(String(100))
    superv_campo = Column(String(200))
    superv_operacao = Column(String(200))
    coordenador = Column(String(200))


# ============================================
# CLASSE: EstruturaEquipesHistorico
# Histórico de estrutura de equipes
# ============================================
class EstruturaEquipesHistorico(Base):
    __tablename__ = "estrutura_equipes_historico"
    
    # Campos de controle do histórico
    id_historico = Column(Integer, primary_key=True, autoincrement=True)
    data_carga = Column(DateTime, nullable=False)
    usuario_carga = Column(Integer)
    observacao = Column(String(500))
    
    # Campos da estrutura original
    id_original = Column(Integer)
    regional = Column(String(100))
    polo = Column(String(100))
    base = Column(String(100))
    prefixo = Column(String(50))
    matricula = Column(String(20))
    colaborador = Column(String(200))
    descr_secao = Column(String(100))
    descr_situacao = Column(String(50))
    placas = Column(String(100))
    tipo_equipe = Column(String(100))
    processo_equipe = Column(String(100))
    superv_campo = Column(String(200))
    superv_operacao = Column(String(200))
    coordenador = Column(String(200))
    
    def __repr__(self):
        return f"<Historico(data_carga={self.data_carga}, colaborador={self.colaborador})>"


# ============================================
# CLASSE: Usuario
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
# CLASSE: MotivoIndisponibilidade
# Representa a tabela MOTIVOS_INDISPONIBILIDADE
# ============================================
class MotivoIndisponibilidade(Base):
    __tablename__ = 'motivos_indisponibilidade'
    
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, unique=True, nullable=False)
    ativo = Column(Boolean, default=True)


# ============================================
# CLASSE: Indisponibilidade
# Representa a tabela INDISPONIBILIDADES
# ============================================
class Indisponibilidade(Base):
    __tablename__ = 'indisponibilidades'
    
    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    eletricista_id = Column(Integer, ForeignKey('estrutura_equipes.id'))
    eletricista2_id = Column(Integer, ForeignKey('estrutura_equipes.id'))
    matricula = Column(String)
    prefixo = Column(String, nullable=False)
    tipo_indisponibilidade = Column(String)  # 'parcial' ou 'total'
    motivo_id = Column(Integer, ForeignKey('motivos_indisponibilidade.id'))
    observacao = Column(Text)
    usuario_registro = Column(Integer, ForeignKey('usuarios.id'))
    criado_em = Column(TIMESTAMP, server_default=func.now())


# ============================================
# CLASSE: EquipeDia
# Controle de frequência - equipes montadas por dia
# ============================================
class EquipeDia(Base):
    __tablename__ = "equipes_dia"
    
    id = Column(Integer, primary_key=True, index=True)
    eletricista_id = Column(Integer, ForeignKey("estrutura_equipes.id"), nullable=False)
    prefixo = Column(String, nullable=False)
    data = Column(Date, nullable=False)
    supervisor_registro = Column(String, nullable=False)
    usuario_registro = Column(Integer, ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, server_default=func.now())
    observacoes = Column(Text)


# ============================================
# CLASSE: Remanejamento
# Remanejamentos temporários de eletricistas
# ============================================
class Remanejamento(Base):
    __tablename__ = "remanejamentos"
    
    id = Column(Integer, primary_key=True, index=True)
    eletricista_id = Column(Integer, ForeignKey("estrutura_equipes.id"), nullable=False)
    supervisor_origem = Column(String, nullable=False)
    supervisor_destino = Column(String, nullable=False)    
    data = Column(Date, nullable=False)
    temporario = Column(Boolean, default=True)
    usuario_registro = Column(Integer, ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, server_default=func.now())
    observacoes = Column(Text)


# ============================================
# FUNÇÃO: Criar tabelas
# ============================================
def criar_tabelas():
    """Cria todas as tabelas no banco de dados"""
    from database import engine
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas com sucesso!")
