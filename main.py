from fastapi import FastAPI, Request, Form, Depends, UploadFile, File
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
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    return usuario

def verificar_autenticacao(request: Request):
    return 'user_id' in request.session

# ==========================================
# FUNÇÕES DE HISTÓRICO
# ==========================================

def arquivar_estrutura_atual(db, usuario_id=None, observacao=None):
    """Copia estrutura atual para histórico"""
    from models import EstruturaEquipes, EstruturaEquipesHistorico
    
    try:
        registros_atuais = db.query(EstruturaEquipes).all()
        
        if not registros_atuais:
            return 0
        
        total_copiados = 0
        data_carga_atual = datetime.now()
        
        for registro in registros_atuais:
            historico = EstruturaEquipesHistorico(
                data_carga=data_carga_atual,
                usuario_carga=usuario_id,
                observacao=observacao,
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
# ROTAS PÚBLICAS
# ========================================

@app.get("/")
def redirecionar_para_login():
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
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
    usuario = db.query(Usuario).filter(Usuario.login == username).first()
    
    if not usuario:
        return templates.TemplateResponse("login.html", {"request": request, "erro": "Usuário não encontrado!"})
    
    if not verificar_senha(password, usuario.senha_hash):
        return templates.TemplateResponse("login.html", {"request": request, "erro": "Senha incorreta!"})
    
    if not usuario.ativo:
        return templates.TemplateResponse("login.html", {"request": request, "erro": "Usuário inativo!"})
    
    request.session['user_id'] = usuario.id
    request.session['user_nome'] = usuario.nome
    request.session['user_perfil'] = usuario.perfil
    request.session['user_base'] = usuario.base_responsavel
    
    return RedirectResponse(url="/home", status_code=302)

# ========================================
# ROTAS PROTEGIDAS
# ========================================

@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse("home.html", {"request": request, "usuario": usuario})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

# ========================================
# ROTAS DO SISTEMA V1 (ANTIGO)
# ========================================

@app.get("/registrar", response_class=HTMLResponse)
def registrar_page(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    from models import MotivoIndisponibilidade
    motivos = db.query(MotivoIndisponibilidade).order_by(MotivoIndisponibilidade.descricao).all()
    hoje = date.today().isoformat()
    
    return templates.TemplateResponse("registrar.html", {"request": request, "usuario": usuario, "motivos": motivos, "hoje": hoje})

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
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    from models import MotivoIndisponibilidade
    motivos = db.query(MotivoIndisponibilidade).order_by(MotivoIndisponibilidade.descricao).all()
    hoje = date.today().isoformat()
    
    return templates.TemplateResponse("registrar.html", {
        "request": request, "usuario": usuario, "motivos": motivos, "hoje": hoje,
        "sucesso": f"Registro simulado! Colaborador: {colaborador}, Tipo: {tipo}"
    })

# ========================================
# ROTAS DO SISTEMA V2 (NOVO)
# ========================================

@app.get("/registrar-v2", response_class=HTMLResponse)
def registrar_v2_page(request: Request, data: str = None, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    from models import EstruturaEquipes, MotivoIndisponibilidade, EquipeDia
    
    if data:
        try:
            data_selecionada = datetime.strptime(data, '%Y-%m-%d').date()
        except:
            data_selecionada = date.today()
    else:
        data_selecionada = date.today()
    
    from models import Indisponibilidade
    
    ids_frequencia = db.query(EquipeDia.eletricista_id).filter(EquipeDia.data == data_selecionada).all()
    ids_indisponivel = db.query(Indisponibilidade.eletricista_id).filter(Indisponibilidade.data == data_selecionada).all()
    
    ids_ja_registrados = set()
    ids_ja_registrados.update([i[0] for i in ids_frequencia])
    ids_ja_registrados.update([i[0] for i in ids_indisponivel])
    ids_ja_registrados = list(ids_ja_registrados)
    
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
                  FROM indisponibilidades indisp 
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
    
    supervisor_campo = usuario.base_responsavel
    query = db.query(EstruturaEquipes)
    query = query.filter(EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA']))
    
    if ids_ja_registrados:
        query = query.filter(~EstruturaEquipes.id.in_(ids_ja_registrados))
    
    if not supervisor_campo or supervisor_campo.upper() == "TODAS":
        eletricistas = query.order_by(EstruturaEquipes.colaborador).all()
        prefixos_supervisor = db.query(EstruturaEquipes.prefixo).distinct().all()
    else:
        from models import Remanejamento
        
        eletricistas_originais = query.filter(EstruturaEquipes.superv_campo == supervisor_campo).all()
        remanejamentos_ativos = db.query(Remanejamento).filter(Remanejamento.data == data_selecionada).all()
        
        remanejamentos_dict = {}
        for r in remanejamentos_ativos:
            remanejamentos_dict[r.eletricista_id] = r.supervisor_destino
        
        eletricistas_filtrados = []
        for elet in eletricistas_originais:
            if elet.id in remanejamentos_dict:
                if remanejamentos_dict[elet.id] != supervisor_campo:
                    continue
            eletricistas_filtrados.append(elet)        
        
        for r in remanejamentos_ativos:
            if r.supervisor_destino == supervisor_campo:
                if r.eletricista_id in ids_ja_registrados:
                    continue
                elet_remanejado = db.query(EstruturaEquipes).filter(EstruturaEquipes.id == r.eletricista_id).first()
                if elet_remanejado:
                    if not any(e.id == elet_remanejado.id for e in eletricistas_filtrados):
                        eletricistas_filtrados.append(elet_remanejado)
        
        eletricistas_filtrados.sort(key=lambda x: x.colaborador)
        eletricistas = eletricistas_filtrados
        prefixos_supervisor = db.query(EstruturaEquipes.prefixo).filter(EstruturaEquipes.superv_campo == supervisor_campo).distinct().all()
    
    prefixos_supervisor = [p[0] for p in prefixos_supervisor if p[0]]
    motivos = db.query(MotivoIndisponibilidade).order_by(MotivoIndisponibilidade.descricao).all()
    
    hoje_formatado = date.today().strftime('%d/%m/%Y')
    hoje_iso = date.today().isoformat()
    data_selecionada_iso = data_selecionada.isoformat()
    data_selecionada_formatada = data_selecionada.strftime('%d/%m/%Y')
    
    return templates.TemplateResponse("registrar_v2.html", {
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
    })


# ==========================================
# ROTA: BUSCAR MOTIVOS DE INDISPONIBILIDADE
# ==========================================
@app.get("/api/motivos-indisponibilidade")
async def buscar_motivos_indisponibilidade(request: Request, db: Session = Depends(get_db)):
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
        
        return {
            "success": True,
            "motivos": [{"id": m.id, "descricao": m.descricao} for m in motivos]
        }
        
    except Exception as e:
        return {"success": False, "erro": str(e)}


# ==========================================
# SALVAR FREQUÊNCIA (PRESENÇA/AUSÊNCIA)
# ==========================================
@app.post("/api/salvar-frequencia")
async def salvar_frequencia(request: Request, db: Session = Depends(get_db)):
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
        
        try:
            data_obj = datetime.strptime(data_registro, '%Y-%m-%d').date()
        except:
            return {"success": False, "erro": "Data inválida"}
        
        motivo_presente = db.execute(
            text("SELECT id FROM motivos_indisponibilidade WHERE UPPER(descricao) = 'PRESENTE'")
        ).fetchone()
        
        if not motivo_presente:
            return {"success": False, "erro": "Motivo 'PRESENTE' não encontrado no banco"}
        
        id_presente = motivo_presente.id
        
        for assoc in associacoes:
            eletricista_id = assoc.get('eletricista_id')
            prefixo = assoc.get('prefixo')
            id_indisponibilidade_recebido = assoc.get('id_indisponibilidade')
            
            if id_indisponibilidade_recebido is None:
                id_indisponibilidade_final = id_presente
            else:
                id_indisponibilidade_final = id_indisponibilidade_recebido
            
            if not eletricista_id or not prefixo:
                continue
            
            ja_existe = db.execute(
                text("SELECT id FROM equipes_dia WHERE eletricista_id = :elet_id AND data = :data"),
                {"elet_id": eletricista_id, "data": data_obj}
            ).fetchone()
            
            if ja_existe:
                db.execute(
                    text("""
                        UPDATE equipes_dia 
                        SET prefixo = :prefixo, supervisor_registro = :supervisor, id_indisponibilidade = :id_indisponibilidade
                        WHERE id = :id
                    """),
                    {"prefixo": prefixo, "supervisor": usuario.base_responsavel or usuario.nome,
                     "id_indisponibilidade": id_indisponibilidade_final, "id": ja_existe.id}
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO equipes_dia (eletricista_id, prefixo, data, supervisor_registro, id_indisponibilidade, usuario_registro)
                        VALUES (:elet_id, :prefixo, :data, :supervisor, :id_indisponibilidade, :usuario_id)
                    """),
                    {"elet_id": eletricista_id, "prefixo": prefixo, "data": data_obj,
                     "supervisor": usuario.base_responsavel or usuario.nome,
                     "id_indisponibilidade": id_indisponibilidade_final, "usuario_id": usuario.id}
                )
        
        db.commit()
        return {"success": True, "data": data_obj.strftime('%d/%m/%Y')}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "erro": str(e)}


@app.post("/api/remanejar-eletricista")
async def remanejar_eletricista(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import Remanejamento, EstruturaEquipes, EquipeDia, Indisponibilidade
    
    try:
        body = await request.json()
        eletricista_id = body.get('eletricista_id')
        
        if not eletricista_id:
            return JSONResponse({"success": False, "erro": "ID do eletricista não informado"})
        
        eletricista = db.query(EstruturaEquipes).filter(EstruturaEquipes.id == eletricista_id).first()
        
        if not eletricista:
            return JSONResponse({"success": False, "erro": "Eletricista não encontrado"})
        
        hoje = date.today()
        
        ja_na_frequencia = db.query(EquipeDia).filter(EquipeDia.eletricista_id == eletricista_id, EquipeDia.data == hoje).first()
        if ja_na_frequencia:
            return JSONResponse({"success": False, "erro": f"❌ {eletricista.colaborador} já foi registrado na FREQUÊNCIA hoje!"})
        
        ja_indisponivel = db.query(Indisponibilidade).filter(Indisponibilidade.eletricista_id == eletricista_id, Indisponibilidade.data == hoje).first()
        if ja_indisponivel:
            return JSONResponse({"success": False, "erro": f"❌ {eletricista.colaborador} já foi registrado como INDISPONÍVEL hoje!"})
        
        remanejamento_existente = db.query(Remanejamento).filter(Remanejamento.eletricista_id == eletricista_id, Remanejamento.data == hoje).first()
        
        if remanejamento_existente:
            if remanejamento_existente.supervisor_destino == usuario.base_responsavel:
                return JSONResponse({"success": False, "erro": f"❌ {eletricista.colaborador} já está remanejado para sua supervisão!"})
            
            supervisor_anterior = remanejamento_existente.supervisor_destino
            remanejamento_existente.supervisor_destino = usuario.base_responsavel or usuario.nome
            remanejamento_existente.usuario_registro = usuario.id
            db.commit()
            return JSONResponse({"success": True, "mensagem": f"✅ {eletricista.colaborador} remanejado de {supervisor_anterior} para sua supervisão!"})
        
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
        
        return JSONResponse({"success": True, "mensagem": f"✅ {eletricista.colaborador} remanejado de {eletricista.superv_campo} para sua supervisão!"})
        
    except Exception as e:
        db.rollback()
        return JSONResponse({"success": False, "erro": str(e)})


@app.post("/api/salvar-indisponibilidade")
async def salvar_indisponibilidade(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import Indisponibilidade, EstruturaEquipes, MotivoIndisponibilidade
    
    try:
        form_data = await request.form()
        
        eletricista_id = form_data.get('eletricista_id')
        prefixo = form_data.get('prefixo')
        tipo_indisponibilidade = form_data.get('tipo_indisponibilidade')
        motivo_id = form_data.get('motivo_id')
        observacoes = form_data.get('observacoes', '')
        data_registro = form_data.get('data', None)
        
        if not tipo_indisponibilidade or tipo_indisponibilidade not in ['parcial', 'total']:
            return JSONResponse({"success": False, "erro": "⚠️ Selecione o tipo de indisponibilidade (Parcial ou Total)"})
        
        if data_registro:
            try:
                data_obj = datetime.strptime(data_registro, '%Y-%m-%d').date()
            except:
                data_obj = date.today()
        else:
            data_obj = date.today()
        
        eletricista = db.query(EstruturaEquipes).filter(EstruturaEquipes.id == eletricista_id).first()
        if not eletricista:
            return JSONResponse({"success": False, "erro": "Eletricista não encontrado"})
        
        ja_indisponivel = db.query(Indisponibilidade).filter(
            Indisponibilidade.eletricista_id == eletricista_id,
            Indisponibilidade.data == data_obj
        ).first()
        
        if ja_indisponivel:
            return JSONResponse({"success": False, "erro": f"❌ {eletricista.colaborador} já foi registrado como INDISPONÍVEL hoje!"})
        
        motivo = db.query(MotivoIndisponibilidade).filter(MotivoIndisponibilidade.id == motivo_id).first()
        if not motivo:
            return JSONResponse({"success": False, "erro": "Motivo inválido"})
        
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
        
        tipo_texto = "Parcial" if tipo_indisponibilidade == "parcial" else "Total"
        
        return JSONResponse({
            "success": True,
            "data": data_obj.strftime('%d/%m/%Y'),
            "mensagem": f"Indisponibilidade {tipo_texto} de {eletricista.colaborador} registrada para {data_obj.strftime('%d/%m/%Y')}!"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({"success": False, "erro": str(e)})


# ========================================
# APIs DE BUSCA
# ========================================

@app.get("/api/buscar-eletricistas")
def buscar_eletricistas(q: str = "", data: str = None, db: Session = Depends(get_db)):
    from models import EstruturaEquipes, Indisponibilidade
    
    if not q or len(q) < 3:
        return JSONResponse({"eletricistas": []})
    
    if data:
        try:
            data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        except:
            data_obj = date.today()
    else:
        data_obj = date.today()
    
    ids_indisponivel = db.query(Indisponibilidade.eletricista_id).filter(Indisponibilidade.data == data_obj).all()
    ids_ja_registrados = [i[0] for i in ids_indisponivel]
    
    query = db.query(EstruturaEquipes).filter(
        EstruturaEquipes.colaborador.ilike(f"%{q}%"),
        EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])
    )
    
    if ids_ja_registrados:
        query = query.filter(~EstruturaEquipes.id.in_(ids_ja_registrados))
    
    eletricistas = query.limit(10).all()
    
    resultado = [{"id": e.id, "nome": e.colaborador, "matricula": e.matricula, "base": e.base, "prefixo": e.prefixo, "polo": e.polo, "regional": e.regional} for e in eletricistas]
    
    return JSONResponse({"eletricistas": resultado})

@app.get("/api/buscar-eletricistas-remanejar")
def buscar_eletricistas_remanejar(q: str = "", data: str = None, db: Session = Depends(get_db)):
    from models import EstruturaEquipes, EquipeDia, Indisponibilidade
    
    if not q or len(q) < 3:
        return JSONResponse({"eletricistas": []})
    
    if data:
        try:
            data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        except:
            data_obj = date.today()
    else:
        data_obj = date.today()
    
    ids_frequencia = db.query(EquipeDia.eletricista_id).filter(EquipeDia.data == data_obj).all()
    ids_indisponivel = db.query(Indisponibilidade.eletricista_id).filter(Indisponibilidade.data == data_obj).all()
    
    ids_bloqueados = set()
    ids_bloqueados.update([i[0] for i in ids_frequencia])
    ids_bloqueados.update([i[0] for i in ids_indisponivel])
    ids_bloqueados = list(ids_bloqueados)
    
    query = db.query(EstruturaEquipes).filter(
        EstruturaEquipes.colaborador.ilike(f"%{q}%"),
        EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])
    )
    
    if ids_bloqueados:
        query = query.filter(~EstruturaEquipes.id.in_(ids_bloqueados))
    
    eletricistas = query.limit(10).all()
    
    resultado = [{"id": e.id, "nome": e.colaborador, "matricula": e.matricula, "base": e.base, "prefixo": e.prefixo, "polo": e.polo, "regional": e.regional, "superv_original": e.superv_campo} for e in eletricistas]
    
    return JSONResponse({"eletricistas": resultado})

@app.get("/api/buscar-prefixos")
def buscar_prefixos(q: str = "", db: Session = Depends(get_db)):
    from models import EstruturaEquipes
    from sqlalchemy import func
    
    if not q or len(q) < 3:
        return JSONResponse({"prefixos": []})
    
    prefixos = db.query(
        EstruturaEquipes.prefixo,
        EstruturaEquipes.base,
        func.count(EstruturaEquipes.id).label('total_eletricistas')
    ).filter(
        EstruturaEquipes.prefixo.ilike(f"%{q}%")
    ).group_by(EstruturaEquipes.prefixo, EstruturaEquipes.base).limit(15).all()
    
    resultado = [{"prefixo": p.prefixo, "base": p.base, "total_eletricistas": p.total_eletricistas} for p in prefixos]
    
    return JSONResponse({"prefixos": resultado})


# ==========================================
# API: BUSCAR REGISTRO PARA DESFAZER
# ==========================================
@app.get("/api/buscar-registro-para-desfazer")
async def buscar_registro_para_desfazer(request: Request, matricula: str, data: str, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    from models import EquipeDia, EstruturaEquipes, MotivoIndisponibilidade
    
    try:
        try:
            data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        except:
            return JSONResponse({"success": False, "erro": "Data inválida"})
        
        eletricista = db.query(EstruturaEquipes).filter(EstruturaEquipes.matricula == matricula.strip()).first()
        
        if not eletricista:
            return JSONResponse({"success": False, "erro": f"❌ Matrícula {matricula} não encontrada!"})
        
        registro = db.query(EquipeDia).filter(EquipeDia.eletricista_id == eletricista.id, EquipeDia.data == data_obj).first()
        
        if not registro:
            return JSONResponse({"success": False, "erro": f"❌ {eletricista.colaborador} não tem registro para {data_obj.strftime('%d/%m/%Y')}!"})
        
        motivo = db.query(MotivoIndisponibilidade).filter(MotivoIndisponibilidade.id == registro.id_indisponibilidade).first()
        tipo = 'presenca' if registro.id_indisponibilidade == 15 else 'ausencia'
        
        return JSONResponse({
            "success": True,
            "eletricista": {"id": eletricista.id, "nome": eletricista.colaborador, "matricula": eletricista.matricula, "prefixo": registro.prefixo},
            "tipo": tipo,
            "motivo": motivo.descricao if motivo else "N/A",
            "data": data_obj.strftime('%d/%m/%Y'),
            "registro_id": registro.id
        })
        
    except Exception as e:
        return JSONResponse({"success": False, "erro": str(e)})


# ==========================================
# API: DESFAZER REGISTRO
# ==========================================
@app.post("/api/desfazer-registro")
async def desfazer_registro(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import EquipeDia, EstruturaEquipes
    
    try:
        dados = await request.json()
        matricula = dados.get('matricula')
        data_str = dados.get('data')
        
        try:
            data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
        except:
            return JSONResponse({"success": False, "erro": "Data inválida"})
        
        eletricista = db.query(EstruturaEquipes).filter(EstruturaEquipes.matricula == matricula.strip()).first()
        
        if not eletricista:
            return JSONResponse({"success": False, "erro": "Eletricista não encontrado"})
        
        registro = db.query(EquipeDia).filter(EquipeDia.eletricista_id == eletricista.id, EquipeDia.data == data_obj).first()
        
        if not registro:
            return JSONResponse({"success": False, "erro": f"{eletricista.colaborador} não tem registro para esta data"})
        
        db.delete(registro)
        db.commit()
        
        return JSONResponse({"success": True, "mensagem": f"Registro de {eletricista.colaborador} removido com sucesso!"})
        
    except Exception as e:
        db.rollback()
        return JSONResponse({"success": False, "erro": str(e)})


# ========================================
# ROTA DE DEBUG
# ========================================

@app.get("/debug-sessao", response_class=HTMLResponse)
def debug_sessao(request: Request):
    logado = verificar_autenticacao(request)
    session_data = {
        'user_id': request.session.get('user_id'),
        'user_nome': request.session.get('user_nome'),
        'user_perfil': request.session.get('user_perfil'),
        'user_base': request.session.get('user_base')
    }
    return templates.TemplateResponse("debug_sessao.html", {"request": request, "logado": logado, "session_data": session_data})


# ========================================
# ROTA DE IMPORTAÇÃO CSV
# ========================================

@app.get("/importar-csv", response_class=HTMLResponse)
def importar_csv_page(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("importar_csv.html", {"request": request, "usuario": usuario})

@app.post("/api/importar-eletricistas")
async def importar_eletricistas(request: Request, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    
    from models import EstruturaEquipes
    import csv
    import io
    
    try:
        total_arquivados = arquivar_estrutura_atual(db=db, usuario_id=usuario.id if usuario else None, observacao="Importação de novo CSV")
        
        contents = await arquivo.read()
        
        try:
            decoded = contents.decode('utf-8')
        except:
            decoded = contents.decode('latin-1')
        
        csv_reader = csv.DictReader(io.StringIO(decoded), delimiter=';')
        
        total_novos = 0
        total_atualizados = 0
        
        for row in csv_reader:
            matricula = str(row.get('matricula', '')).strip()
            colaborador = str(row.get('colaborador', '')).strip()
            
            if not matricula or not colaborador:
                continue
            
            eletricista_existente = db.query(EstruturaEquipes).filter(EstruturaEquipes.matricula == matricula).first()
            
            if eletricista_existente:
                eletricista_existente.colaborador = colaborador
                eletricista_existente.prefixo = str(row.get('prefixo', '')).strip()
                eletricista_existente.base = str(row.get('base', '')).strip()
                eletricista_existente.polo = str(row.get('polo', '')).strip()
                eletricista_existente.regional = str(row.get('regional', '')).strip()
                eletricista_existente.superv_campo = str(row.get('superv_campo', '')).strip()
                eletricista_existente.superv_operacao = str(row.get('superv_operacao', '')).strip()
                eletricista_existente.coordenador = str(row.get('coordenador', '')).strip()
                eletricista_existente.descr_secao = str(row.get('descr_secao', '')).strip()
                eletricista_existente.descr_situacao = str(row.get('descr_situacao', '')).strip()
                eletricista_existente.placas = str(row.get('placas', '')).strip()
                eletricista_existente.tipo_equipe = str(row.get('tipo_equipe', '')).strip()
                eletricista_existente.processo_equipe = str(row.get('processo_equipe', '')).strip()
                total_atualizados += 1
            else:
                novo_eletricista = EstruturaEquipes(
                    colaborador=colaborador,
                    matricula=matricula,
                    prefixo=str(row.get('prefixo', '')).strip(),
                    base=str(row.get('base', '')).strip(),
                    polo=str(row.get('polo', '')).strip(),
                    regional=str(row.get('regional', '')).strip(),
                    superv_campo=str(row.get('superv_campo', '')).strip(),
                    superv_operacao=str(row.get('superv_operacao', '')).strip(),
                    coordenador=str(row.get('coordenador', '')).strip(),
                    descr_secao=str(row.get('descr_secao', '')).strip(),
                    descr_situacao=str(row.get('descr_situacao', '')).strip(),
                    placas=str(row.get('placas', '')).strip(),
                    tipo_equipe=str(row.get('tipo_equipe', '')).strip(),
                    processo_equipe=str(row.get('processo_equipe', '')).strip()
                )
                db.add(novo_eletricista)
                total_novos += 1
        
        db.commit()
        
        return JSONResponse({
            "success": True,
            "total_arquivados": total_arquivados,
            "total_novos": total_novos,
            "total_atualizados": total_atualizados,
            "mensagem": f"✅ Importação concluída!\n\n📦 {total_arquivados} registros arquivados\n📥 {total_novos} novos + {total_atualizados} atualizados"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({"success": False, "erro": f"Erro: {str(e)}"})


@app.get("/api/teste-eletricistas")
def teste_eletricistas(db: Session = Depends(get_db)):
    from models import EstruturaEquipes
    try:
        total = db.query(EstruturaEquipes).count()
        todos = db.query(EstruturaEquipes).limit(5).all()
        resultado = [{"id": e.id, "colaborador": e.colaborador, "matricula": e.matricula, "prefixo": e.prefixo} for e in todos]
        return JSONResponse({"total_no_banco": total, "primeiros_5": resultado})
    except Exception as e:
        return JSONResponse({"erro": str(e)})

@app.get("/api/listar-todos-eletricistas")
def listar_todos_eletricistas(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    from models import EstruturaEquipes
    try:
        eletricistas = db.query(EstruturaEquipes).all()
        resultado = [{"id": e.id, "colaborador": e.colaborador, "matricula": e.matricula, "prefixo": e.prefixo, "base": e.base, "polo": e.polo, "regional": e.regional, "superv_campo": e.superv_campo} for e in eletricistas]
        return JSONResponse({"success": True, "total": len(resultado), "eletricistas": resultado})
    except Exception as e:
        return JSONResponse({"success": False, "erro": str(e)})

@app.get("/api/teste-motivos")
def teste_motivos(db: Session = Depends(get_db)):
    from models import MotivoIndisponibilidade
    try:
        motivos = db.query(MotivoIndisponibilidade).all()
        resultado = [{"id": m.id, "descricao": m.descricao, "ativo": m.ativo} for m in motivos]
        return JSONResponse({"total": len(resultado), "motivos": resultado})
    except Exception as e:
        return JSONResponse({"erro": str(e)})

@app.get("/api/criar-motivos-padrao")
def criar_motivos_padrao(db: Session = Depends(get_db)):
    from models import MotivoIndisponibilidade
    
    motivos_corretos = ["ATESTADO MEDICO", "FALTA INJUSTIFICADA", "VIATURA COM DEFEITO", "VIATURA EM MANUTENCAO", "ACIDENTE", "TREINAMENTO", "FERIAS", "LICENCA", "OUTRO"]
    
    try:
        total_criado = 0
        for descricao in motivos_corretos:
            existe = db.query(MotivoIndisponibilidade).filter(MotivoIndisponibilidade.descricao == descricao).first()
            if not existe:
                db.add(MotivoIndisponibilidade(descricao=descricao, ativo=True))
                total_criado += 1
        db.commit()
        return JSONResponse({"success": True, "total_criado": total_criado, "mensagem": f"✅ {total_criado} motivos criados!"})
    except Exception as e:
        db.rollback()
        return JSONResponse({"success": False, "erro": str(e)})


# ========================================
# ROTAS DE GESTÃO DE USUÁRIOS
# ========================================

@app.get("/usuarios", response_class=HTMLResponse)
def listar_usuarios(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    if usuario.perfil != 'admin':
        return templates.TemplateResponse("home.html", {"request": request, "usuario": usuario, "erro": "⚠️ Acesso negado! Apenas administradores podem gerenciar usuários."})
    
    usuarios = db.query(Usuario).order_by(Usuario.nome).all()
    return templates.TemplateResponse("usuarios.html", {"request": request, "usuario": usuario, "usuarios": usuarios})


@app.get("/usuarios/novo", response_class=HTMLResponse)
def novo_usuario_page(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    if usuario.perfil != 'admin':
        return RedirectResponse(url="/usuarios")
    
    from models import EstruturaEquipes
    supervisores = db.query(EstruturaEquipes.superv_campo).distinct().all()
    supervisores = [s[0] for s in supervisores if s[0]]
    supervisores.append("Todas")
    
    return templates.TemplateResponse("usuario_form.html", {"request": request, "usuario": usuario, "supervisores": supervisores, "usuario_edicao": None})


@app.post("/usuarios/novo")
def criar_usuario(
    request: Request,
    nome: str = Form(...),
    login: str = Form(...),
    senha: str = Form(...),
    perfil: str = Form(...),
    base_responsavel: str = Form(""),
    ativo: bool = Form(False),
    db: Session = Depends(get_db)
):
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario_logado = get_usuario_logado(request, db)
    if not usuario_logado or usuario_logado.perfil != 'admin':
        return RedirectResponse(url="/usuarios")
    
    from auth import criar_hash_senha
    from models import EstruturaEquipes
    
    try:
        existe = db.query(Usuario).filter(Usuario.login == login).first()
        if existe:
            supervisores = db.query(EstruturaEquipes.superv_campo).distinct().all()
            supervisores = [s[0] for s in supervisores if s[0]]
            supervisores.append("Todas")
            return templates.TemplateResponse("usuario_form.html", {"request": request, "usuario": usuario_logado, "supervisores": supervisores, "usuario_edicao": None, "erro": f"❌ Login '{login}' já existe!"})
        
        novo_usuario = Usuario(
            nome=nome, login=login, senha_hash=criar_hash_senha(senha),
            perfil=perfil, base_responsavel=base_responsavel if base_responsavel else None, ativo=ativo
        )
        db.add(novo_usuario)
        db.commit()
        return RedirectResponse(url=f"/usuarios?sucesso=Usuário '{nome}' criado com sucesso!", status_code=302)
        
    except Exception as e:
        db.rollback()
        supervisores = db.query(EstruturaEquipes.superv_campo).distinct().all()
        supervisores = [s[0] for s in supervisores if s[0]]
        supervisores.append("Todas")
        return templates.TemplateResponse("usuario_form.html", {"request": request, "usuario": usuario_logado, "supervisores": supervisores, "usuario_edicao": None, "erro": f"❌ Erro: {str(e)}"})


@app.get("/usuarios/editar/{user_id}", response_class=HTMLResponse)
def editar_usuario_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    if usuario.perfil != 'admin':
        return RedirectResponse(url="/usuarios")
    
    usuario_edicao = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not usuario_edicao:
        return RedirectResponse(url="/usuarios?erro=Usuário não encontrado!")
    
    from models import EstruturaEquipes
    supervisores = db.query(EstruturaEquipes.superv_campo).distinct().all()
    supervisores = [s[0] for s in supervisores if s[0]]
    supervisores.append("Todas")
    
    return templates.TemplateResponse("usuario_form.html", {"request": request, "usuario": usuario, "supervisores": supervisores, "usuario_edicao": usuario_edicao})


@app.post("/usuarios/editar/{user_id}")
def salvar_edicao_usuario(
    request: Request,
    user_id: int,
    nome: str = Form(...),
    perfil: str = Form(...),
    base_responsavel: str = Form(""),
    ativo: bool = Form(False),
    db: Session = Depends(get_db)
):
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario_logado = get_usuario_logado(request, db)
    if not usuario_logado or usuario_logado.perfil != 'admin':
        return RedirectResponse(url="/usuarios")
    
    try:
        usuario_edicao = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not usuario_edicao:
            return RedirectResponse(url="/usuarios?erro=Usuário não encontrado!")
        
        usuario_edicao.nome = nome
        usuario_edicao.perfil = perfil
        usuario_edicao.base_responsavel = base_responsavel if base_responsavel else None
        usuario_edicao.ativo = ativo
        db.commit()
        return RedirectResponse(url=f"/usuarios?sucesso=Usuário '{nome}' atualizado!", status_code=302)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url=f"/usuarios?erro=Erro: {str(e)}", status_code=302)


# ========================================
# APIs DE GESTÃO DE USUÁRIOS
# ========================================

@app.post("/api/usuarios/toggle-status")
async def toggle_status_usuario(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario_logado = get_usuario_logado(request, db)
    if not usuario_logado or usuario_logado.perfil != 'admin':
        return JSONResponse({"success": False, "erro": "Acesso negado"})
    
    try:
        body = await request.json()
        user_id = body.get('user_id')
        ativo = body.get('ativo')
        
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not usuario:
            return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
        
        if usuario.id == usuario_logado.id:
            return JSONResponse({"success": False, "erro": "Você não pode desativar sua própria conta!"})
        
        usuario.ativo = ativo
        db.commit()
        
        acao = "ativado" if ativo else "desativado"
        return JSONResponse({"success": True, "mensagem": f"Usuário '{usuario.nome}' {acao} com sucesso!"})
        
    except Exception as e:
        db.rollback()
        return JSONResponse({"success": False, "erro": str(e)})


@app.post("/api/usuarios/resetar-senha")
async def resetar_senha_usuario(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario_logado = get_usuario_logado(request, db)
    if not usuario_logado or usuario_logado.perfil != 'admin':
        return JSONResponse({"success": False, "erro": "Acesso negado"})
    
    from auth import criar_hash_senha
    
    try:
        body = await request.json()
        user_id = body.get('user_id')
        nova_senha = body.get('nova_senha')
        
        if not nova_senha or len(nova_senha) < 6:
            return JSONResponse({"success": False, "erro": "Senha deve ter no mínimo 6 caracteres"})
        
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not usuario:
            return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
        
        usuario.senha_hash = criar_hash_senha(nova_senha)
        db.commit()
        return JSONResponse({"success": True, "mensagem": f"Senha de '{usuario.nome}' resetada com sucesso!"})
        
    except Exception as e:
        db.rollback()
        return JSONResponse({"success": False, "erro": str(e)})


# ========================================
# ROTAS DE RELATÓRIOS
# ========================================

@app.get("/relatorios", response_class=HTMLResponse)
def relatorios_page(request: Request, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    from models import EstruturaEquipes
    
    supervisores = db.query(EstruturaEquipes.superv_campo).distinct().all()
    supervisores = [s[0] for s in supervisores if s[0]]
    
    hoje = date.today()
    inicio_mes = date(hoje.year, hoje.month, 1)
    
    return templates.TemplateResponse("relatorios.html", {
        "request": request, "usuario": usuario, "supervisores": supervisores,
        "hoje_iso": hoje.isoformat(), "inicio_mes": inicio_mes.isoformat()
    })


@app.get("/api/relatorio-geral")
def relatorio_geral(request: Request, data_inicio: str = None, data_fim: str = None, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import EstruturaEquipes, EquipeDia, Indisponibilidade, MotivoIndisponibilidade
    
    try:
        if data_inicio and data_fim:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        elif data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = data_inicio_obj
        else:
            data_inicio_obj = date.today()
            data_fim_obj = date.today()
        
        total_eletricistas = db.query(EstruturaEquipes).filter(EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])).count()
        
        dias_periodo = []
        data_atual = data_inicio_obj
        while data_atual <= data_fim_obj:
            dias_periodo.append(data_atual)
            data_atual += timedelta(days=1)
        
        resultado = {"PRESENTE": 0, "NÃO REGISTRADO": 0}
        
        for dia in dias_periodo:
            ids_presentes = db.query(EquipeDia.eletricista_id).filter(EquipeDia.data == dia).all()
            ids_presentes = set([p[0] for p in ids_presentes])
            resultado["PRESENTE"] += len(ids_presentes)
            
            indisponiveis = db.query(Indisponibilidade.eletricista_id, MotivoIndisponibilidade.descricao).join(
                MotivoIndisponibilidade, Indisponibilidade.motivo_id == MotivoIndisponibilidade.id
            ).filter(Indisponibilidade.data == dia).all()
            
            ids_indisponiveis = set([i[0] for i in indisponiveis])
            
            for elet_id, motivo in indisponiveis:
                motivo_upper = motivo.upper()
                if motivo_upper not in resultado:
                    resultado[motivo_upper] = 0
                resultado[motivo_upper] += 1
            
            ids_registrados = ids_presentes.union(ids_indisponiveis)
            total_nao_registrados = db.query(EstruturaEquipes.id).filter(
                EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA']),
                ~EstruturaEquipes.id.in_(list(ids_registrados))
            ).count()
            resultado["NÃO REGISTRADO"] += total_nao_registrados
        
        total_registros = sum(v for k, v in resultado.items() if k != "NÃO REGISTRADO")
        total_geral = sum(resultado.values())
        
        dados_relatorio = []
        for motivo, qtde in resultado.items():
            percentual = (qtde / total_geral * 100) if total_geral > 0 else 0
            dados_relatorio.append({"motivo": motivo, "qtde": qtde, "percentual": round(percentual, 1)})
        
        dados_relatorio.sort(key=lambda x: (0 if x['motivo'] == 'PRESENTE' else 2 if x['motivo'] == 'NÃO REGISTRADO' else 1, x['motivo']))
        
        return JSONResponse({
            "success": True,
            "periodo": {"inicio": data_inicio_obj.strftime('%d/%m/%Y'), "fim": data_fim_obj.strftime('%d/%m/%Y'), "dias": len(dias_periodo)},
            "total_eletricistas": total_eletricistas,
            "total_registros": total_registros,
            "dados": dados_relatorio
        })
        
    except Exception as e:
        return JSONResponse({"success": False, "erro": str(e)})


@app.get("/api/relatorio-por-supervisor")
def relatorio_por_supervisor(request: Request, data_inicio: str = None, data_fim: str = None, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import EstruturaEquipes, EquipeDia, Indisponibilidade, MotivoIndisponibilidade
    
    try:
        if data_inicio and data_fim:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        elif data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = data_inicio_obj
        else:
            data_inicio_obj = date.today()
            data_fim_obj = date.today()
        
        dias_periodo = []
        data_atual = data_inicio_obj
        while data_atual <= data_fim_obj:
            dias_periodo.append(data_atual)
            data_atual += timedelta(days=1)
        
        supervisores = db.query(EstruturaEquipes.superv_campo).filter(EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])).distinct().all()
        supervisores = [s[0] for s in supervisores if s[0]]
        
        motivos_db = db.query(MotivoIndisponibilidade.descricao).all()
        todos_motivos = set([m[0] for m in motivos_db])
        
        dados_supervisores = []
        
        for supervisor in supervisores:
            total_eletricistas_sup = db.query(EstruturaEquipes).filter(
                EstruturaEquipes.superv_campo == supervisor,
                EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])
            ).count()
            
            contadores = {"Presente": 0, "Não registrado": 0}
            
            for dia in dias_periodo:
                presentes = db.query(EquipeDia.eletricista_id).join(
                    EstruturaEquipes, EquipeDia.eletricista_id == EstruturaEquipes.id
                ).filter(EquipeDia.data == dia, EstruturaEquipes.superv_campo == supervisor).all()
                
                ids_presentes = set([p[0] for p in presentes])
                contadores["Presente"] += len(ids_presentes)
                
                indisponiveis = db.query(Indisponibilidade.eletricista_id, MotivoIndisponibilidade.descricao).join(
                    MotivoIndisponibilidade, Indisponibilidade.motivo_id == MotivoIndisponibilidade.id
                ).join(EstruturaEquipes, Indisponibilidade.eletricista_id == EstruturaEquipes.id).filter(
                    Indisponibilidade.data == dia, EstruturaEquipes.superv_campo == supervisor
                ).all()
                
                ids_indisponiveis = set([i[0] for i in indisponiveis])
                
                for elet_id, motivo in indisponiveis:
                    if motivo not in contadores:
                        contadores[motivo] = 0
                    contadores[motivo] += 1
                
                ids_registrados = ids_presentes.union(ids_indisponiveis)
                nao_registrados = db.query(EstruturaEquipes.id).filter(
                    EstruturaEquipes.superv_campo == supervisor,
                    EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA']),
                    ~EstruturaEquipes.id.in_(list(ids_registrados)) if ids_registrados else True
                ).count()
                contadores["Não registrado"] += nao_registrados
            
            total_registros = sum(contadores.values())
            percentual_presenca = (contadores["Presente"] / total_registros * 100) if total_registros > 0 else 0
            
            dados_supervisores.append({
                "supervisor": supervisor,
                "total_eletricistas": total_eletricistas_sup,
                "contadores": contadores,
                "total_registros": total_registros,
                "percentual_presenca": round(percentual_presenca, 1)
            })
        
        dados_supervisores.sort(key=lambda x: x['percentual_presenca'], reverse=True)
        total_geral = sum([s['total_registros'] for s in dados_supervisores])
        
        return JSONResponse({
            "success": True,
            "periodo": {"inicio": data_inicio_obj.strftime('%d/%m/%Y'), "fim": data_fim_obj.strftime('%d/%m/%Y'), "dias": len(dias_periodo)},
            "todos_motivos": sorted(list(todos_motivos)),
            "dados": dados_supervisores,
            "total_geral": total_geral
        })
        
    except Exception as e:
        return JSONResponse({"success": False, "erro": str(e)})


@app.get("/api/relatorio-por-prefixo")
def relatorio_por_prefixo(request: Request, data_inicio: str = None, data_fim: str = None, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import Indisponibilidade, MotivoIndisponibilidade
    
    try:
        if data_inicio and data_fim:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        elif data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = data_inicio_obj
        else:
            data_inicio_obj = date.today()
            data_fim_obj = date.today()
        
        dias_periodo = []
        data_atual = data_inicio_obj
        while data_atual <= data_fim_obj:
            dias_periodo.append(data_atual)
            data_atual += timedelta(days=1)
        
        dados_por_prefixo = {}
        
        for dia in dias_periodo:
            indisponiveis = db.query(
                Indisponibilidade.prefixo, MotivoIndisponibilidade.descricao,
                Indisponibilidade.data, Indisponibilidade.eletricista_id
            ).join(MotivoIndisponibilidade, Indisponibilidade.motivo_id == MotivoIndisponibilidade.id).filter(
                Indisponibilidade.data == dia
            ).order_by(Indisponibilidade.prefixo, Indisponibilidade.id).all()
            
            for prefixo, motivo, data, elet_id in indisponiveis:
                if prefixo:
                    chave = (prefixo, data)
                    if chave not in dados_por_prefixo:
                        dados_por_prefixo[chave] = []
                    if len(dados_por_prefixo[chave]) < 2:
                        dados_por_prefixo[chave].append(motivo)
        
        dados_prefixos = []
        for (prefixo, data), motivos in dados_por_prefixo.items():
            dados_prefixos.append({
                "prefixo": prefixo,
                "data": data.strftime('%d/%m/%Y'),
                "motivo1": motivos[0] if len(motivos) > 0 else "-",
                "motivo2": motivos[1] if len(motivos) > 1 else "-"
            })
        
        dados_prefixos.sort(key=lambda x: (x['prefixo'], x['data']))
        prefixos_unicos = set([d['prefixo'] for d in dados_prefixos])
        
        return JSONResponse({
            "success": True,
            "periodo": {"inicio": data_inicio_obj.strftime('%d/%m/%Y'), "fim": data_fim_obj.strftime('%d/%m/%Y'), "dias": len(dias_periodo)},
            "total_prefixos": len(prefixos_unicos),
            "total_registros": len(dados_prefixos),
            "dados": dados_prefixos
        })
        
    except Exception as e:
        return JSONResponse({"success": False, "erro": str(e)})


@app.get("/api/relatorio-eletricistas-disponiveis")
def relatorio_eletricistas_disponiveis(request: Request, data_inicio: str = None, data_fim: str = None, db: Session = Depends(get_db)):
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import EstruturaEquipes, EquipeDia, Indisponibilidade
    
    try:
        if data_inicio and data_fim:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        elif data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = data_inicio_obj
        else:
            data_inicio_obj = date.today()
            data_fim_obj = date.today()
        
        dias_periodo = []
        data_atual = data_inicio_obj
        while data_atual <= data_fim_obj:
            dias_periodo.append(data_atual)
            data_atual += timedelta(days=1)
        
        todos_eletricistas = db.query(EstruturaEquipes).filter(EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])).all()
        eletricistas_com_registro = {}
        
        for dia in dias_periodo:
            presentes = db.query(EquipeDia.eletricista_id).filter(EquipeDia.data == dia).distinct().all()
            for (eletricista_id,) in presentes:
                if eletricista_id:
                    if eletricista_id not in eletricistas_com_registro:
                        eletricistas_com_registro[eletricista_id] = set()
                    eletricistas_com_registro[eletricista_id].add(dia)
            
            indisponiveis = db.query(Indisponibilidade.eletricista_id).filter(Indisponibilidade.data == dia).distinct().all()
            for (eletricista_id,) in indisponiveis:
                if eletricista_id:
                    if eletricista_id not in eletricistas_com_registro:
                        eletricistas_com_registro[eletricista_id] = set()
                    eletricistas_com_registro[eletricista_id].add(dia)
        
        dados_disponiveis = []
        for eletricista in todos_eletricistas:
            if eletricista.id not in eletricistas_com_registro:
                dados_disponiveis.append({
                    "polo": eletricista.polo or "-",
                    "base": eletricista.base or "-",
                    "matricula": eletricista.matricula,
                    "colaborador": eletricista.colaborador,
                    "processo_equipe": eletricista.processo_equipe or "-",
                    "superv_campo": eletricista.superv_campo or "-",
                    "superv_operacao": eletricista.superv_operacao or "-"
                })
        
        dados_disponiveis.sort(key=lambda x: (x['polo'], x['base'], x['matricula']))
        
        return JSONResponse({
            "success": True,
            "periodo": {"inicio": data_inicio_obj.strftime('%d/%m/%Y'), "fim": data_fim_obj.strftime('%d/%m/%Y'), "dias": len(dias_periodo)},
            "total_eletricistas": len(todos_eletricistas),
            "total_disponiveis": len(dados_disponiveis),
            "dados": dados_disponiveis
        })
        
    except Exception as e:
        return JSONResponse({"success": False, "erro": str(e)})


@app.get("/api/debug-indisponibilidades")
def debug_indisponibilidades(request: Request, db: Session = Depends(get_db)):
    from models import Indisponibilidade, MotivoIndisponibilidade, EstruturaEquipes
    
    resultado = {"status": "DEBUG ATIVO", "data_atual": str(date.today()), "resultados": {}}
    
    try:
        total_indisp = db.query(Indisponibilidade).count()
        resultado["resultados"]["total_indisponibilidades"] = total_indisp
        
        motivos = db.query(MotivoIndisponibilidade.id, MotivoIndisponibilidade.descricao).all()
        resultado["resultados"]["motivos_cadastrados"] = [{"id": m[0], "descricao": m[1]} for m in motivos]
        
        return JSONResponse(resultado)
        
    except Exception as e:
        resultado["erro"] = str(e)
        return JSONResponse(resultado)


# ========================================
# EXECUTAR SERVIDOR
# ========================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
