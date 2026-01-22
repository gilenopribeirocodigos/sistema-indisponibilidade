from sqlalchemy import Column, Integer, String, Boolean, Date, Text, ForeignKey, TIMESTAMP, DateTime
from sqlalchemy.sql import func
from database import Base
from datetime import datetime  # ← ADICIONE ESTA LINHA

# ==========================================
# HISTÓRICO DE ESTRUTURA DE EQUIPES
# ==========================================

class EstruturaEquipesHistorico(Base):
    __tablename__ = "estrutura_equipes_historico"
    
    # ========================================
    # CAMPOS DE CONTROLE DO HISTÓRICO
    # ========================================
    id_historico = Column(Integer, primary_key=True, autoincrement=True)
    data_carga = Column(DateTime, nullable=False, default=datetime.now)
    usuario_carga = Column(Integer)
    observacao = Column(String(500))
    
    # ========================================
    # CAMPOS DA ESTRUTURA ORIGINAL (TODOS!)
    # ========================================
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
    tipo_indisponibilidade = Column(String)  # ← NOVO! 'parcial' ou 'total'
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
    usuario_registro = Column(Integer, ForeignKey("usuarios.id"))  # ← ADICIONAR
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
    data = Column(Date, nullable=False)
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

# ==========================================
# MODELO: Histórico de Estrutura de Equipes
# ==========================================

from sqlalchemy import Column, Integer, String, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class EstruturaEquipesHistorico(Base):
    __tablename__ = "estrutura_equipes_historico"
    
    # Chave primária própria do histórico
    id_historico = Column(Integer, primary_key=True, autoincrement=True)
    
    # Campos de controle do histórico
    data_carga = Column(DateTime, nullable=False, default=datetime.now)
    usuario_carga = Column(String(100))
    observacao = Column(String(500))  # Opcional: motivo da carga
    
    # Campos originais da estrutura_equipes (copiar TODOS os campos)
    id_original = Column(Integer)  # ID do registro original
    matricula = Column(String(20))
    colaborador = Column(String(200))
    polo = Column(String(100))
    superv_campo = Column(String(200))
    base = Column(String(100))
    prefixo = Column(String(50))
    descr_situacao = Column(String(50))
    # ... adicionar TODOS os outros campos que existem em estrutura_equipes
    
    def __repr__(self):
        return f"<Historico(data_carga={self.data_carga}, colaborador={self.colaborador})>"


# ==========================================
# FUNÇÃO: Arquivar estrutura atual
# ==========================================

def arquivar_estrutura_atual(db, usuario_id=None, observacao=None):
    """
    Copia toda a estrutura atual para o histórico antes de uma nova importação
    """
    from models import EstruturaEquipes  # Importar modelo atual
    
    try:
        # Buscar todos os registros atuais
        registros_atuais = db.query(EstruturaEquipes).all()
        
        if not registros_atuais:
            print("⚠️ Nenhum registro para arquivar")
            return 0
        
        # Copiar cada registro para o histórico
        total_copiados = 0
        data_carga_atual = datetime.now()
        
        for registro in registros_atuais:
            historico = EstruturaEquipesHistorico(
                data_carga=data_carga_atual,
                usuario_carga=usuario_id,
                observacao=observacao,
                
                # Copiar todos os campos do registro original
                id_original=registro.id,
                matricula=registro.matricula,
                colaborador=registro.colaborador,
                polo=registro.polo,
                superv_campo=registro.superv_campo,
                base=registro.base,
                prefixo=registro.prefixo,
                descr_situacao=registro.descr_situacao,
                # ... copiar TODOS os outros campos
            )
            
            db.add(historico)
            total_copiados += 1
        
        db.commit()
        
        print(f"✅ {total_copiados} registros arquivados em {data_carga_atual}")
        return total_copiados
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao arquivar: {e}")
        raise


# ==========================================
# FUNÇÃO: Restaurar de uma data específica
# ==========================================

def restaurar_historico(db, data_carga):
    """
    Restaura a estrutura de uma data específica do histórico
    """
    from models import EstruturaEquipes
    
    try:
        # Buscar registros históricos da data
        historicos = db.query(EstruturaEquipesHistorico).filter(
            EstruturaEquipesHistorico.data_carga == data_carga
        ).all()
        
        if not historicos:
            print(f"⚠️ Nenhum histórico encontrado para {data_carga}")
            return 0
        
        # Limpar estrutura atual
        db.query(EstruturaEquipes).delete()
        
        # Restaurar registros do histórico
        total_restaurados = 0
        for hist in historicos:
            registro = EstruturaEquipes(
                matricula=hist.matricula,
                colaborador=hist.colaborador,
                polo=hist.polo,
                superv_campo=hist.superv_campo,
                base=hist.base,
                prefixo=hist.prefixo,
                descr_situacao=hist.descr_situacao,
                # ... todos os outros campos
            )
            
            db.add(registro)
            total_restaurados += 1
        
        db.commit()
        
        print(f"✅ {total_restaurados} registros restaurados de {data_carga}")
        return total_restaurados
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao restaurar: {e}")
        raise


# ==========================================
# FUNÇÃO: Listar datas de cargas disponíveis
# ==========================================

def listar_datas_historico(db):
    """
    Lista todas as datas de carga disponíveis no histórico
    """
    from sqlalchemy import func
    
    datas = db.query(
        EstruturaEquipesHistorico.data_carga,
        func.count(EstruturaEquipesHistorico.id_historico).label('total_registros'),
        EstruturaEquipesHistorico.usuario_carga,
        EstruturaEquipesHistorico.observacao
    ).group_by(
        EstruturaEquipesHistorico.data_carga,
        EstruturaEquipesHistorico.usuario_carga,
        EstruturaEquipesHistorico.observacao
    ).order_by(
        EstruturaEquipesHistorico.data_carga.desc()
    ).all()
    
    return [
        {
            "data_carga": d[0].strftime('%d/%m/%Y %H:%M:%S'),
            "total_registros": d[1],
            "usuario": d[2] or "Sistema",
            "observacao": d[3] or ""
        }
        for d in datas
    ]








