from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from models import Usuario
from auth import verificar_senha
import uvicorn
import os
from datetime import date, datetime, timedelta
import logging
from pathlib import Path

# ✅ CONFIGURAR LOGGER
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar paths
BASE_DIR = Path(__file__).resolve().parent

# Porta dinâmica para Render
PORT = int(os.getenv("PORT", 8000))

# Inicializar FastAPI
app = FastAPI(title="Sistema de Indisponibilidade")

# Criar tabelas automaticamente na inicialização
@app.on_event("startup")
async def startup_event():
    """Executado quando o servidor inicia"""
    from models import criar_tabelas, Usuario
    from auth import criar_hash_senha
    from database import SessionLocal
    
    # Criar tabelas
    criar_tabelas()
    print("✅ Tabelas criadas!")
    
    # Criar usuário admin se não existir
    db = SessionLocal()
    try:
        admin = db.query(Usuario).filter(Usuario.login == "admin").first()
        if not admin:
            novo_admin = Usuario(
                nome="Administrador",
                login="admin",
                senha_hash=criar_hash_senha("admin123"),
                perfil="admin",
                base_responsavel="Todas",
                ativo=True
            )
            db.add(novo_admin)
            db.commit()
            print("✅ Usuário admin criado!")
        else:
            print("✅ Usuário admin já existe!")
    except Exception as e:
        print(f"❌ Erro ao criar admin: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("🚀 Sistema iniciado!")

# Configurar middleware de sessões (IMPORTANTE!)
SECRET_KEY = os.getenv('SECRET_KEY', 'chave-secreta-padrao-mude-isso')
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Configurar templates e arquivos estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ========================================
# FUNÇÕES AUXILIARES DE SESSÃO
# ========================================

def get_usuario_logado(request: Request, db: Session = Depends(get_db)):
    """
    Retorna o usuário logado ou None.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    
    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    return usuario

def verificar_autenticacao(request: Request):
    """
    Verifica se há usuário na sessão.
    Retorna True se logado, False caso contrário.
    """
    return 'user_id' in request.session

# ==========================================
# FUNÇÕES DE HISTÓRICO
# ==========================================

def arquivar_estrutura_atual(db, usuario_id=None, observacao=None):
    """Copia estrutura atual para histórico"""
    from models import EstruturaEquipes, EstruturaEquipesHistorico
    from datetime import datetime
    
    try:
        registros_atuais = db.query(EstruturaEquipes).all()
        
        if not registros_atuais:
            return 0
        
        total_copiados = 0
        data_carga_atual = datetime.now()
        
        for registro in registros_atuais:
            historico = EstruturaEquipesHistorico(
                # Campos de controle
                data_carga=data_carga_atual,
                usuario_carga=usuario_id,
                observacao=observacao,
                
                # Campos da estrutura original (TODOS!)
                id_original=registro.id,
                regional=registro.regional,
                polo=registro.polo,
                base=registro.base,
                prefixo=registro.prefixo,
                matricula=registro.matricula,
                colaborador=registro.colaborador,
                descr_secao=registro.descr_secao,
                descr_situacao=registro.descr_situacao,
                placas=registro.placas,
                tipo_equipe=registro.tipo_equipe,
                processo_equipe=registro.processo_equipe,
                superv_campo=registro.superv_campo,
                superv_operacao=registro.superv_operacao,
                coordenador=registro.coordenador
            )
            
            db.add(historico)
            total_copiados += 1
        
        db.commit()
        return total_copiados
        
    except Exception as e:
        db.rollback()
        raise

def listar_datas_historico(db):
    """Lista todas as datas de carga disponíveis"""
    from models import EstruturaEquipesHistorico
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

def restaurar_historico(db, data_carga):
    """Restaura estrutura de uma data específica"""
    from models import EstruturaEquipes, EstruturaEquipesHistorico
    
    try:
        historicos = db.query(EstruturaEquipesHistorico).filter(
            EstruturaEquipesHistorico.data_carga == data_carga
        ).all()
        
        if not historicos:
            return 0
        
        db.query(EstruturaEquipes).delete()
        
        total_restaurados = 0
        for hist in historicos:
            registro = EstruturaEquipes(
                regional=hist.regional,
                polo=hist.polo,
                base=hist.base,
                prefixo=hist.prefixo,
                matricula=hist.matricula,
                colaborador=hist.colaborador,
                descr_secao=hist.descr_secao,
                descr_situacao=hist.descr_situacao,
                placas=hist.placas,
                tipo_equipe=hist.tipo_equipe,
                processo_equipe=hist.processo_equipe,
                superv_campo=hist.superv_campo,
                superv_operacao=hist.superv_operacao,
                coordenador=hist.coordenador
            )
            
            db.add(registro)
            total_restaurados += 1
        
        db.commit()
        return total_restaurados
        
    except Exception as e:
        db.rollback()
        raise

# ========================================
# ROTAS PÚBLICAS (não precisa estar logado)
# ========================================

@app.get("/")
def redirecionar_para_login():
    """Redireciona para login ou home conforme autenticação."""
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Página de login."""
    # Se já está logado, redireciona para home
    if verificar_autenticacao(request):
        return RedirectResponse(url="/home")
    
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def processar_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Processa o login e cria sessão."""
    
    # Buscar usuário no banco
    usuario = db.query(Usuario).filter(Usuario.login == username).first()
    
    # Verificar se usuário existe
    if not usuario:
        return templates.TemplateResponse(
            "login.html", 
            {
                "request": request, 
                "erro": "Usuário não encontrado!"
            }
        )
    
    # Verificar se senha está correta
    if not verificar_senha(password, usuario.senha_hash):
        return templates.TemplateResponse(
            "login.html", 
            {
                "request": request, 
                "erro": "Senha incorreta!"
            }
        )
    
    # Verificar se usuário está ativo
    if not usuario.ativo:
        return templates.TemplateResponse(
            "login.html", 
            {
                "request": request, 
                "erro": "Usuário inativo!"
            }
        )
    
    # Login bem-sucedido! Criar sessão
    request.session['user_id'] = usuario.id
    request.session['user_nome'] = usuario.nome
    request.session['user_perfil'] = usuario.perfil
    request.session['user_base'] = usuario.base_responsavel
    
    # Redirecionar para home
    return RedirectResponse(url="/home", status_code=302)

# ========================================
# ROTAS PROTEGIDAS (precisa estar logado)
# ========================================

@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request, db: Session = Depends(get_db)):
    """Página inicial (protegida - só acessa se logado)."""
    
    # Verificar se está logado
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    # Buscar dados do usuário
    usuario = get_usuario_logado(request, db)
    
    if not usuario:
        # Sessão inválida, limpar e redirecionar
        request.session.clear()
        return RedirectResponse(url="/login")
    
    # Renderizar página home
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "usuario": usuario
        }
    )

@app.get("/logout")
def logout(request: Request):
    """Desloga o usuário (limpa a sessão)."""
    request.session.clear()
    return RedirectResponse(url="/login")

# ========================================
# ROTAS DO SISTEMA V1 (ANTIGO)
# ========================================

@app.get("/registrar", response_class=HTMLResponse)
def registrar_page(request: Request, db: Session = Depends(get_db)):
    """Página de registro de indisponibilidade."""
    
    # Verificar se está logado
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    # Buscar usuário
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    # Buscar motivos do banco
    from models import MotivoIndisponibilidade
    motivos = db.query(MotivoIndisponibilidade).order_by(MotivoIndisponibilidade.descricao).all()
    
    # Data de hoje
    hoje = date.today().isoformat()
    
    return templates.TemplateResponse(
        "registrar.html",
        {
            "request": request,
            "usuario": usuario,
            "motivos": motivos,
            "hoje": hoje
        }
    )

@app.post("/registrar")
def processar_registro(
    request: Request,
    tipo: str = Form(...),
    colaborador: str = Form(...),
    prefixo: str = Form(...),
    motivo_id: int = Form(...),
    observacoes: str = Form(""),
    data_inicio: str = Form(None),
    data_fim: str = Form(None),
    db: Session = Depends(get_db)
):
    """Processa o registro de indisponibilidade."""
    
    # Verificar autenticação
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    # Por enquanto, apenas mostra mensagem de sucesso
    # Na próxima etapa vamos salvar no banco
    
    from models import MotivoIndisponibilidade
    motivos = db.query(MotivoIndisponibilidade).order_by(MotivoIndisponibilidade.descricao).all()
    hoje = date.today().isoformat()
    
    return templates.TemplateResponse(
        "registrar.html",
        {
            "request": request,
            "usuario": usuario,
            "motivos": motivos,
            "hoje": hoje,
            "sucesso": f"Registro simulado! Colaborador: {colaborador}, Tipo: {tipo}"
        }
    )

# ========================================
# ROTAS DO SISTEMA V2 (NOVO)
# ========================================

@app.get("/registrar-v2", response_class=HTMLResponse)
def registrar_v2_page(
    request: Request, 
    data: str = None,
    db: Session = Depends(get_db)
):
    """Página de registro V2 - Interface dinâmica com filtro de data"""
    
    # Verificar se está logado
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    from models import EstruturaEquipes, MotivoIndisponibilidade, EquipeDia
    
    # Definir data (hoje ou data selecionada)
    if data:
        try:
            data_selecionada = datetime.strptime(data, '%Y-%m-%d').date()
        except:
            data_selecionada = date.today()
    else:
        data_selecionada = date.today()
    
    # Buscar IDs dos eletricistas já registrados na data selecionada
    from models import Indisponibilidade
    
    # 1. Registrados na FREQUÊNCIA
    ids_frequencia = db.query(EquipeDia.eletricista_id).filter(
        EquipeDia.data == data_selecionada
    ).all()
    
    # 2. Registrados como INDISPONÍVEIS
    ids_indisponivel = db.query(Indisponibilidade.eletricista_id).filter(
        Indisponibilidade.data == data_selecionada
    ).all()
    
    # 3. JUNTAR AMBOS (usar set para eliminar duplicatas)
    ids_ja_registrados = set()
    ids_ja_registrados.update([i[0] for i in ids_frequencia])
    ids_ja_registrados.update([i[0] for i in ids_indisponivel])
    
    # Converter de volta para lista
    ids_ja_registrados = list(ids_ja_registrados)
    
    
    
    # EXCLUINDO os que já foram registrados na tabela indisponibilidade
    # ✅ BUSCAR ELETRICISTAS AUSENTES (para seção Indisponível)
    # EXCLUINDO os que já foram registrados na tabela indisponibilidade
    eletricistas_ausentes = db.execute(
        text("""
            SELECT 
                ed.id AS equipe_dia_id,
                ed.eletricista_id,
                ed.prefixo,
                ee.colaborador,
                ee.matricula,
                mi.descricao AS motivo_ausencia
            FROM equipes_dia ed
            JOIN estrutura_equipes ee ON ed.eletricista_id = ee.id
            JOIN motivos_indisponibilidade mi ON ed.id_indisponibilidade = mi.id
            WHERE ed.data = :data
              AND ed.id_indisponibilidade != 15
              AND NOT EXISTS (
                  SELECT 1 
                  FROM indisponibilidade indisp 
                  WHERE indisp.eletricista_id = ed.eletricista_id 
                    AND indisp.data = ed.data
              )
            ORDER BY ee.colaborador
        """),
        {"data": data_selecionada}
    ).fetchall()
       
    eletricistas_ausentes_lista = [
        {
            "id": e.eletricista_id,
            "equipe_dia_id": e.equipe_dia_id,
            "nome": e.colaborador,
            "matricula": e.matricula,
            "prefixo": e.prefixo,
            "motivo_ausencia": e.motivo_ausencia
        }
        for e in eletricistas_ausentes
    ]
    
    # Buscar eletricistas CONSIDERANDO REMANEJAMENTOS
    supervisor_campo = usuario.base_responsavel
    
    # Criar query base
    query = db.query(EstruturaEquipes)

    # ✅ FILTRAR APENAS ATIVOS E RESERVAS
    query = query.filter(
        EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])
    )  
    
    # EXCLUIR eletricistas já registrados na data selecionada
    if ids_ja_registrados:
        query = query.filter(~EstruturaEquipes.id.in_(ids_ja_registrados))
    
    # Se for ADMIN ou base "Todas", mostra TODOS (que ainda não foram registrados)
    if not supervisor_campo or supervisor_campo.upper() == "TODAS":
        eletricistas = query.order_by(EstruturaEquipes.colaborador).all()
        
        # Buscar todos os prefixos únicos
        prefixos_supervisor = db.query(EstruturaEquipes.prefixo).distinct().all()
    else:
        # PARA SUPERVISORES: CONSIDERAR REMANEJAMENTOS ATIVOS
        from models import Remanejamento
        
        # 1. Buscar eletricistas ORIGINAIS da supervisão
        eletricistas_originais = query.filter(
            EstruturaEquipes.superv_campo == supervisor_campo
        ).all()
        
        # 2. Buscar remanejamentos ATIVOS para a data selecionada
        remanejamentos_ativos = db.query(Remanejamento).filter(
            Remanejamento.data == data_selecionada
        ).all()
        
        # 3. Criar dicionário de remanejamentos: {eletricista_id: destino}
        remanejamentos_dict = {}
        for r in remanejamentos_ativos:
            remanejamentos_dict[r.eletricista_id] = r.supervisor_destino
        
        # 4. FILTRAR eletricistas: REMOVER os remanejados PARA OUTRA BASE
        eletricistas_filtrados = []
        for elet in eletricistas_originais:
            # Se foi remanejado para outra base, NÃO mostrar
            if elet.id in remanejamentos_dict:
                if remanejamentos_dict[elet.id] != supervisor_campo:
                    continue  # Pula (foi para outra base)
            eletricistas_filtrados.append(elet)        
        
        # 5. ADICIONAR eletricistas que foram REMANEJADOS PARA ESTA BASE
        for r in remanejamentos_ativos:
            if r.supervisor_destino == supervisor_campo:
                # ✅ NÃO adicionar se já foi registrado (Frequência ou Indisponibilidade)
                if r.eletricista_id in ids_ja_registrados:
                    continue  # Pula este eletricista
                
                # Buscar dados do eletricista remanejado
                elet_remanejado = db.query(EstruturaEquipes).filter(
                    EstruturaEquipes.id == r.eletricista_id
                ).first()
                
                if elet_remanejado:
                    # Verificar se já não está na lista (evitar duplicatas)
                    if not any(e.id == elet_remanejado.id for e in eletricistas_filtrados):
                        eletricistas_filtrados.append(elet_remanejado)
        
        # Ordenar por nome
        eletricistas_filtrados.sort(key=lambda x: x.colaborador)
        eletricistas = eletricistas_filtrados
        
        # Buscar prefixos da supervisão
        prefixos_supervisor = db.query(EstruturaEquipes.prefixo).filter(
            EstruturaEquipes.superv_campo == supervisor_campo
        ).distinct().all()
    
    prefixos_supervisor = [p[0] for p in prefixos_supervisor if p[0]]
    
    # Buscar motivos
    motivos = db.query(MotivoIndisponibilidade).order_by(
        MotivoIndisponibilidade.descricao
    ).all()
    
    # Formatar datas
    hoje_formatado = date.today().strftime('%d/%m/%Y')
    hoje_iso = date.today().isoformat()
    data_selecionada_iso = data_selecionada.isoformat()
    data_selecionada_formatada = data_selecionada.strftime('%d/%m/%Y')
    
    return templates.TemplateResponse(
        "registrar_v2.html",
        {
            "request": request,
            "usuario": usuario,
            "eletricistas_disponiveis": eletricistas,
            "total_eletricistas": len(eletricistas),
            "eletricistas_ausentes": eletricistas_ausentes_lista,
            "prefixos_supervisor": prefixos_supervisor,
            "motivos": motivos,
            "hoje": hoje_formatado,
            "hoje_iso": hoje_iso,
            "data_selecionada": data_selecionada_iso,
            "data_selecionada_formatada": data_selecionada_formatada
        }
    )


# ==========================================
# ROTA: BUSCAR MOTIVOS DE INDISPONIBILIDADE
# ==========================================
@app.get("/api/motivos-indisponibilidade")
async def buscar_motivos_indisponibilidade(request: Request, db: Session = Depends(get_db)):
    """
    Retorna lista de motivos EXCETO 'PRESENTE'
    Para usar no select de ausência
    """
    # ✅ ADICIONAR VERIFICAÇÃO DE AUTENTICAÇÃO
    if not verificar_autenticacao(request):
        return {"success": False, "erro": "Não autenticado"}
    
    try:
        motivos = db.execute(
            text("""
                SELECT id, descricao 
                FROM motivos_indisponibilidade 
                WHERE ativo = true 
                  AND UPPER(descricao) != 'PRESENTE'
                ORDER BY descricao
            """)
        ).fetchall()
        
        logger.info(f"✅ Retornando {len(motivos)} motivos de indisponibilidade")
        
        return {
            "success": True,
            "motivos": [
                {"id": m.id, "descricao": m.descricao} 
                for m in motivos
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar motivos: {str(e)}")
        return {"success": False, "erro": str(e)}

# ==========================================
# SALVAR FREQUÊNCIA (PRESENÇA/AUSÊNCIA)
# ==========================================
@app.post("/api/salvar-frequencia")
async def salvar_frequencia(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Salvar frequência (presença ou ausência)
    """
    # Verificar autenticação
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    try:
        dados = await request.json()
        associacoes = dados.get('associacoes', [])
        data_registro = dados.get('data')
        
        if not associacoes:
            return {"success": False, "erro": "Nenhuma associação fornecida"}
        
        if not data_registro:
            return {"success": False, "erro": "Data não fornecida"}
        
        # Converter data
        try:
            data_obj = datetime.strptime(data_registro, '%Y-%m-%d').date()
        except:
            return {"success": False, "erro": "Data inválida"}
        
        # ✅ BUSCAR ID DO MOTIVO "PRESENTE"
        motivo_presente = db.execute(
            text("SELECT id FROM motivos_indisponibilidade WHERE UPPER(descricao) = 'PRESENTE'")
        ).fetchone()
        
        if not motivo_presente:
            return {"success": False, "erro": "Motivo 'PRESENTE' não encontrado no banco"}
        
        id_presente = motivo_presente.id
        
        logger.info(f"📋 Salvando {len(associacoes)} associação(ões)...")
        
        # Inserir cada associação
        for assoc in associacoes:
            eletricista_id = assoc.get('eletricista_id')
            prefixo = assoc.get('prefixo')
            id_indisponibilidade_recebido = assoc.get('id_indisponibilidade')
            
            # ✅ LÓGICA CORRIGIDA:
            # Se id_indisponibilidade for None ou null → PRESENÇA (usar id_presente)
            # Se id_indisponibilidade tiver um valor → AUSÊNCIA (usar o valor recebido)
            if id_indisponibilidade_recebido is None:
                id_indisponibilidade_final = id_presente
                logger.info(f"   ✅ PRESENÇA: Eletricista {eletricista_id} → Motivo ID {id_presente}")
            else:
                id_indisponibilidade_final = id_indisponibilidade_recebido
                logger.info(f"   ⚠️ AUSÊNCIA: Eletricista {eletricista_id} → Motivo ID {id_indisponibilidade_recebido}")
            
            if not eletricista_id or not prefixo:
                logger.warning(f"   ⚠️ Associação inválida: eletricista_id={eletricista_id}, prefixo={prefixo}")
                continue
            
            # Verificar se já existe registro
            ja_existe = db.execute(
                text("""
                    SELECT id FROM equipes_dia 
                    WHERE eletricista_id = :elet_id 
                      AND data = :data
                """),
                {"elet_id": eletricista_id, "data": data_obj}
            ).fetchone()
            
            if ja_existe:
                # Atualizar
                logger.info(f"   🔄 Atualizando registro existente ID {ja_existe.id}")
                db.execute(
                    text("""
                        UPDATE equipes_dia 
                        SET prefixo = :prefixo,
                            supervisor_registro = :supervisor,
                            id_indisponibilidade = :id_indisponibilidade
                        WHERE id = :id
                    """),
                    {
                        "prefixo": prefixo,
                        "supervisor": usuario.base_responsavel or usuario.nome,
                        "id_indisponibilidade": id_indisponibilidade_final,
                        "id": ja_existe.id
                    }
                )
            else:
                # Inserir novo
                logger.info(f"   ➕ Inserindo novo registro")
                db.execute(
                    text("""
                        INSERT INTO equipes_dia 
                        (eletricista_id, prefixo, data, supervisor_registro, id_indisponibilidade, usuario_registro)
                        VALUES (:elet_id, :prefixo, :data, :supervisor, :id_indisponibilidade, :usuario_id)
                    """),
                    {
                        "elet_id": eletricista_id,
                        "prefixo": prefixo,
                        "data": data_obj,
                        "supervisor": usuario.base_responsavel or usuario.nome,
                        "id_indisponibilidade": id_indisponibilidade_final,
                        "usuario_id": usuario.id
                    }
                )
        
        db.commit()
        logger.info(f"✅ Salvamento concluído com sucesso!")
        
        return {
            "success": True,
            "data": data_obj.strftime('%d/%m/%Y')
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao salvar frequência: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "erro": str(e)}


@app.post("/api/remanejar-eletricista")
async def remanejar_eletricista(
    request: Request,
    db: Session = Depends(get_db)
):
    """Remanejar eletricista temporariamente"""
    
    # Verificar autenticação
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import Remanejamento, EstruturaEquipes, EquipeDia, Indisponibilidade
    
    try:
        # Ler JSON do body
        body = await request.json()
        eletricista_id = body.get('eletricista_id')
        
        if not eletricista_id:
            return JSONResponse({"success": False, "erro": "ID do eletricista não informado"})
        
        # Buscar eletricista
        eletricista = db.query(EstruturaEquipes).filter(
            EstruturaEquipes.id == eletricista_id
        ).first()
        
        if not eletricista:
            return JSONResponse({"success": False, "erro": "Eletricista não encontrado"})
        
        hoje = date.today()
        
        # ✅ VALIDAÇÃO 1: Verificar se já está na FREQUÊNCIA
        ja_na_frequencia = db.query(EquipeDia).filter(
            EquipeDia.eletricista_id == eletricista_id,
            EquipeDia.data == hoje
        ).first()
        
        if ja_na_frequencia:
            return JSONResponse({
                "success": False,
                "erro": f"❌ {eletricista.colaborador} já foi registrado na FREQUÊNCIA hoje! Não pode ser remanejado."
            })
        
        # ✅ VALIDAÇÃO 2: Verificar se já está INDISPONÍVEL
        ja_indisponivel = db.query(Indisponibilidade).filter(
            Indisponibilidade.eletricista_id == eletricista_id,
            Indisponibilidade.data == hoje
        ).first()
        
        if ja_indisponivel:
            return JSONResponse({
                "success": False,
                "erro": f"❌ {eletricista.colaborador} já foi registrado como INDISPONÍVEL hoje! Não pode ser remanejado."
            })
        
        # ✅ VALIDAÇÃO 3: Verificar se já existe remanejamento
        remanejamento_existente = db.query(Remanejamento).filter(
            Remanejamento.eletricista_id == eletricista_id,
            Remanejamento.data == hoje
        ).first()
        
        if remanejamento_existente:
            # Se já está remanejado para ESTA supervisão
            if remanejamento_existente.supervisor_destino == usuario.base_responsavel:
                return JSONResponse({
                    "success": False,
                    "erro": f"❌ {eletricista.colaborador} já está remanejado para sua supervisão!"
                })
            
            # Se está remanejado para OUTRA supervisão → ATUALIZAR
            supervisor_anterior = remanejamento_existente.supervisor_destino
            remanejamento_existente.supervisor_destino = usuario.base_responsavel or usuario.nome
            remanejamento_existente.usuario_registro = usuario.id
            db.commit()
            
            return JSONResponse({
                "success": True,
                "mensagem": f"✅ {eletricista.colaborador} remanejado de {supervisor_anterior} para sua supervisão!"
            })
        
        # ✅ CRIAR NOVO REMANEJAMENTO
        novo_remanejamento = Remanejamento(
            eletricista_id=eletricista_id,
            supervisor_origem=eletricista.superv_campo,
            supervisor_destino=usuario.base_responsavel or usuario.nome,
            data=hoje,
            temporario=True,
            usuario_registro=usuario.id
        )
        
        db.add(novo_remanejamento)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "mensagem": f"✅ {eletricista.colaborador} remanejado de {eletricista.superv_campo} para sua supervisão!"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "erro": str(e)
        })


@app.post("/api/salvar-indisponibilidade")
async def salvar_indisponibilidade(
    request: Request,
    db: Session = Depends(get_db)
):
    """Salvar registro de indisponibilidade"""
    
    # Verificar autenticação
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import Indisponibilidade, EstruturaEquipes, MotivoIndisponibilidade
    
    try:
        # Ler dados do formulário
        form_data = await request.form()
        
        eletricista_id = form_data.get('eletricista_id')
        prefixo = form_data.get('prefixo')
        tipo_indisponibilidade = form_data.get('tipo_indisponibilidade')
        motivo_id = form_data.get('motivo_id')
        observacoes = form_data.get('observacoes', '')
        data_registro = form_data.get('data', None)
        
        # Validar tipo_indisponibilidade
        if not tipo_indisponibilidade or tipo_indisponibilidade not in ['parcial', 'total']:
            return JSONResponse({
                "success": False, 
                "erro": "⚠️ Selecione o tipo de indisponibilidade (Parcial ou Total)"
            })
        
        # Definir data
        if data_registro:
            try:
                data_obj = datetime.strptime(data_registro, '%Y-%m-%d').date()
            except:
                data_obj = date.today()
        else:
            data_obj = date.today()
        
        # Validar eletricista
        eletricista = db.query(EstruturaEquipes).filter(
            EstruturaEquipes.id == eletricista_id
        ).first()
        
        if not eletricista:
            return JSONResponse({"success": False, "erro": "Eletricista não encontrado"})
        
        # ✅ REMOVIDA A VALIDAÇÃO "já foi registrado na FREQUÊNCIA"
        # Agora permite registrar indisponibilidade mesmo se já está na frequência
        
        # Verificar se já foi registrado como INDISPONÍVEL hoje
        ja_indisponivel = db.query(Indisponibilidade).filter(
            Indisponibilidade.eletricista_id == eletricista_id,
            Indisponibilidade.data == data_obj
        ).first()
        
        if ja_indisponivel:
            return JSONResponse({
                "success": False,
                "erro": f"❌ {eletricista.colaborador} já foi registrado como INDISPONÍVEL hoje!"
            })
        
        # Validar motivo
        motivo = db.query(MotivoIndisponibilidade).filter(
            MotivoIndisponibilidade.id == motivo_id
        ).first()
        
        if not motivo:
            return JSONResponse({"success": False, "erro": "Motivo inválido"})
        
        # Criar indisponibilidade
        nova_indisponibilidade = Indisponibilidade(
            data=data_obj,
            eletricista_id=eletricista_id,
            matricula=eletricista.matricula,
            prefixo=prefixo,
            tipo_indisponibilidade=tipo_indisponibilidade,
            motivo_id=motivo_id,
            observacao=observacoes if observacoes else None,
            usuario_registro=usuario.id
        )
        
        db.add(nova_indisponibilidade)
        db.commit()
        
        # Mensagem com tipo
        tipo_texto = "Parcial" if tipo_indisponibilidade == "parcial" else "Total"
        
        return JSONResponse({
            "success": True,
            "data": data_obj.strftime('%d/%m/%Y'),
            "mensagem": f"Indisponibilidade {tipo_texto} de {eletricista.colaborador} registrada para {data_obj.strftime('%d/%m/%Y')}!"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "erro": str(e)
        })


# ========================================
# APIs DE BUSCA
# ========================================

@app.get("/api/buscar-eletricistas")
def buscar_eletricistas(
    q: str = "", 
    data: str = None,
    db: Session = Depends(get_db)
):
    """
    API para buscar eletricistas por nome.
    Para INDISPONIBILIDADE: exclui apenas os já registrados como indisponíveis.
    """
    from models import EstruturaEquipes, Indisponibilidade
    
    # Verificar se tem termo de busca
    if not q or len(q) < 3:
        return JSONResponse({"eletricistas": []})
    
    # Definir data (hoje ou data informada)
    if data:
        try:
            data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        except:
            data_obj = date.today()
    else:
        data_obj = date.today()
    
    # IMPORTANTE: Para busca de INDISPONIBILIDADE, 
    # EXCLUIR APENAS os já registrados como INDISPONÍVEIS
    # (não excluir os da frequência, pois eles podem ficar indisponíveis)
    
    ids_indisponivel = db.query(Indisponibilidade.eletricista_id).filter(
        Indisponibilidade.data == data_obj
    ).all()
    
    ids_ja_registrados = [i[0] for i in ids_indisponivel]
    
    # Buscar eletricistas (case-insensitive) EXCLUINDO os já registrados como indisponíveis
    query = db.query(EstruturaEquipes).filter(
        EstruturaEquipes.colaborador.ilike(f"%{q}%"),        
        EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])
    )
    
    # EXCLUIR apenas os já registrados como INDISPONÍVEIS
    if ids_ja_registrados:
        query = query.filter(~EstruturaEquipes.id.in_(ids_ja_registrados))
    
    eletricistas = query.limit(10).all()
    
    # Formatar resultado
    resultado = []
    for elet in eletricistas:
        resultado.append({
            "id": elet.id,
            "nome": elet.colaborador,
            "matricula": elet.matricula,
            "base": elet.base,
            "prefixo": elet.prefixo,
            "polo": elet.polo,
            "regional": elet.regional
        })
    
    return JSONResponse({"eletricistas": resultado})

@app.get("/api/buscar-eletricistas-remanejar")
def buscar_eletricistas_remanejar(
    q: str = "", 
    data: str = None,
    db: Session = Depends(get_db)
):
    """
    API para buscar eletricistas para REMANEJAMENTO.
    Exclui apenas os já registrados em Frequência ou Indisponibilidade.
    NÃO exclui os já remanejados (para permitir atualização).
    """
    from models import EstruturaEquipes, EquipeDia, Indisponibilidade
    
    # Verificar se tem termo de busca
    if not q or len(q) < 3:
        return JSONResponse({"eletricistas": []})
    
    # Definir data (hoje ou data informada)
    if data:
        try:
            data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        except:
            data_obj = date.today()
    else:
        data_obj = date.today()
    
    # Buscar IDs dos eletricistas que NÃO podem ser remanejados
    # 1. Registrados na FREQUÊNCIA (qualquer base)
    ids_frequencia = db.query(EquipeDia.eletricista_id).filter(
        EquipeDia.data == data_obj
    ).all()
    
    # 2. Registrados como INDISPONÍVEIS (qualquer base)
    ids_indisponivel = db.query(Indisponibilidade.eletricista_id).filter(
        Indisponibilidade.data == data_obj
    ).all()
    
    # Juntar IDs (NÃO incluir remanejamentos aqui!)
    ids_bloqueados = set()
    ids_bloqueados.update([i[0] for i in ids_frequencia])
    ids_bloqueados.update([i[0] for i in ids_indisponivel])
    
    ids_bloqueados = list(ids_bloqueados)
    
    # Buscar eletricistas (case-insensitive) EXCLUINDO os bloqueados
    query = db.query(EstruturaEquipes).filter(
        EstruturaEquipes.colaborador.ilike(f"%{q}%"),
        EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])
    )
    
    # EXCLUIR apenas os em Frequência ou Indisponíveis
    if ids_bloqueados:
        query = query.filter(~EstruturaEquipes.id.in_(ids_bloqueados))
    
    eletricistas = query.limit(10).all()
    
    # Formatar resultado
    resultado = []
    for elet in eletricistas:
        resultado.append({
            "id": elet.id,
            "nome": elet.colaborador,
            "matricula": elet.matricula,
            "base": elet.base,
            "prefixo": elet.prefixo,
            "polo": elet.polo,
            "regional": elet.regional,
            "superv_original": elet.superv_campo
        })
    
    return JSONResponse({"eletricistas": resultado})

@app.get("/api/buscar-prefixos")
def buscar_prefixos(q: str = "", db: Session = Depends(get_db)):
    """
    API para buscar prefixos de equipes.
    Retorna JSON com lista de prefixos únicos que correspondem à busca.
    """
    from models import EstruturaEquipes
    from sqlalchemy import func
    
    # Verificar se tem termo de busca
    if not q or len(q) < 3:
        return JSONResponse({"prefixos": []})
    
    # Buscar prefixos únicos (case-insensitive)
    # Agrupa por prefixo e conta quantas equipes têm esse prefixo
    prefixos = db.query(
        EstruturaEquipes.prefixo,
        EstruturaEquipes.base,
        func.count(EstruturaEquipes.id).label('total_eletricistas')
    ).filter(
        EstruturaEquipes.prefixo.ilike(f"%{q}%")
    ).group_by(
        EstruturaEquipes.prefixo,
        EstruturaEquipes.base
    ).limit(15).all()
    
    # Formatar resultado
    resultado = []
    for prefixo_obj in prefixos:
        resultado.append({
            "prefixo": prefixo_obj.prefixo,
            "base": prefixo_obj.base,
            "total_eletricistas": prefixo_obj.total_eletricistas
        })
    
    return JSONResponse({"prefixos": resultado})


# [CONTINUAR COM TODAS AS OUTRAS ROTAS DO SEU ARQUIVO ORIGINAL...]
# (Gestão de usuários, relatórios, importação CSV, etc.)

# ========================================
# EXECUTAR SERVIDOR
# ========================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)



