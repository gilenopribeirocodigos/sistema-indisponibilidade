"""
Script de Debug - Verificar Indisponibilidades
Execute este script no servidor para verificar os dados no banco de dados
"""

from database import SessionLocal
from models import Indisponibilidade, MotivoIndisponibilidade, EstruturaEquipes
from datetime import date

def verificar_indisponibilidades():
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("DEBUG - VERIFICAÇÃO DE INDISPONIBILIDADES")
        print("="*60)
        
        # 1. Verificar se há registros de indisponibilidade
        print("\n1. Total de registros na tabela Indisponibilidade:")
        total_indisp = db.query(Indisponibilidade).count()
        print(f"   Total: {total_indisp}")
        
        if total_indisp == 0:
            print("\n   ⚠️ PROBLEMA: Não há registros de indisponibilidade!")
            print("   Solução: Registre uma indisponibilidade pelo sistema")
            return
        
        # 2. Mostrar alguns registros
        print("\n2. Últimos 5 registros de indisponibilidade:")
        ultimos = db.query(Indisponibilidade).order_by(Indisponibilidade.id.desc()).limit(5).all()
        for indisp in ultimos:
            print(f"   - ID: {indisp.id}, Eletricista ID: {indisp.eletricista_id}, Data: {indisp.data}, Motivo ID: {indisp.motivo_id}")
        
        # 3. Verificar motivos
        print("\n3. Motivos cadastrados:")
        motivos = db.query(MotivoIndisponibilidade).all()
        for motivo in motivos:
            print(f"   - ID: {motivo.id}, Descrição: '{motivo.descricao}'")
        
        # 4. Fazer a consulta igual ao relatório
        print("\n4. Teste da consulta do relatório (data de hoje):")
        hoje = date.today()
        print(f"   Data: {hoje}")
        
        indisponiveis = db.query(
            Indisponibilidade.eletricista_id,
            MotivoIndisponibilidade.descricao
        ).join(
            MotivoIndisponibilidade,
            Indisponibilidade.motivo_id == MotivoIndisponibilidade.id
        ).join(
            EstruturaEquipes,
            Indisponibilidade.eletricista_id == EstruturaEquipes.id
        ).filter(
            Indisponibilidade.data == hoje
        ).all()
        
        print(f"   Registros encontrados: {len(indisponiveis)}")
        for elet_id, motivo in indisponiveis:
            print(f"   - Eletricista ID: {elet_id}, Motivo: '{motivo}'")
        
        # 5. Verificar registros sem data de hoje
        print("\n5. Indisponibilidades com outras datas:")
        outras_datas = db.query(
            Indisponibilidade.data,
            MotivoIndisponibilidade.descricao
        ).join(
            MotivoIndisponibilidade,
            Indisponibilidade.motivo_id == MotivoIndisponibilidade.id
        ).filter(
            Indisponibilidade.data != hoje
        ).limit(10).all()
        
        if outras_datas:
            print(f"   Encontrados {len(outras_datas)} registros em outras datas:")
            for data, motivo in outras_datas:
                print(f"   - Data: {data}, Motivo: '{motivo}'")
        else:
            print("   Nenhum registro em outras datas")
        
        # 6. Verificar estrutura da tabela Indisponibilidade
        print("\n6. Verificar campos da tabela Indisponibilidade:")
        primeira = db.query(Indisponibilidade).first()
        if primeira:
            print(f"   ID: {primeira.id}")
            print(f"   Eletricista ID: {primeira.eletricista_id}")
            print(f"   Motivo ID: {primeira.motivo_id}")
            print(f"   Data: {primeira.data}")
            print(f"   Tipo: {getattr(primeira, 'tipo', 'N/A')}")
            print(f"   Data Início: {getattr(primeira, 'data_inicio', 'N/A')}")
            print(f"   Data Fim: {getattr(primeira, 'data_fim', 'N/A')}")
        
        print("\n" + "="*60)
        print("FIM DO DEBUG")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verificar_indisponibilidades()
