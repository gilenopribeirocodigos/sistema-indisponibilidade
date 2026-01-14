from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from database import get_db
from models import Usuario
from auth import verificar_senha
import uvicorn
import os
from datetime import date
import os
from pathlib import Path

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
    from models import criar_tabelas
    criar_tabelas()
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

def get_usuario_logado(request: Request, db: Session):
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
def registrar_v2_page(request: Request, db: Session = Depends(get_db)):
    """Página de registro V2 - Interface dinâmica"""
    
    # Verificar se está logado
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    from models import EstruturaEquipes, MotivoIndisponibilidade
    
    # Buscar APENAS eletricistas da supervisão do usuário
    supervisor_campo = usuario.base_responsavel
    
    if supervisor_campo:
        eletricistas = db.query(EstruturaEquipes).filter(
            EstruturaEquipes.superv_campo == supervisor_campo
        ).order_by(EstruturaEquipes.colaborador).all()
    else:
        # Se for ADMIN, mostra todos (ou ajuste conforme sua regra)
        eletricistas = db.query(EstruturaEquipes).order_by(
            EstruturaEquipes.colaborador
        ).limit(50).all()
    
    # Buscar prefixos únicos da supervisão
    prefixos_supervisor = db.query(EstruturaEquipes.prefixo).filter(
        EstruturaEquipes.superv_campo == supervisor_campo
    ).distinct().all() if supervisor_campo else []
    
    prefixos_supervisor = [p[0] for p in prefixos_supervisor if p[0]]
    
    # Buscar motivos
    motivos = db.query(MotivoIndisponibilidade).order_by(
        MotivoIndisponibilidade.descricao
    ).all()
    
    # Data de hoje
    hoje = date.today().strftime('%d/%m/%Y')
    
    return templates.TemplateResponse(
        "registrar_v2.html",
        {
            "request": request,
            "usuario": usuario,
            "eletricistas": eletricistas,
            "prefixos_supervisor": prefixos_supervisor,
            "motivos": motivos,
            "hoje": hoje
        }
    )


@app.post("/api/salvar-frequencia")
async def salvar_frequencia(
    request: Request,
    db: Session = Depends(get_db)
):
    """Salvar associações de frequência em lote"""
    
    # Verificar autenticação
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import EquipeDia
    
    try:
        # Ler JSON do body
        body = await request.json()
        associacoes = body.get('associacoes', [])
        
        if not associacoes:
            return JSONResponse({"success": False, "erro": "Nenhuma associação enviada"})
        
        # Data de hoje
        hoje = date.today()
        
        # Salvar cada associação
        total_salvo = 0
        for assoc in associacoes:
            nova_equipe = EquipeDia(
                eletricista_id=assoc['eletricista_id'],
                prefixo=assoc['prefixo'],
                data=hoje,
                supervisor_registro=usuario.base_responsavel or usuario.nome
            )
            db.add(nova_equipe)
            total_salvo += 1
        
        db.commit()
        
        return JSONResponse({
            "success": True,
            "total": total_salvo,
            "mensagem": f"{total_salvo} associação(ões) salva(s) com sucesso!"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "erro": str(e)
        })


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
    
    from models import Remanejamento, EstruturaEquipes
    
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
        
        # Verificar se já foi remanejado hoje
        hoje = date.today()
        ja_remanejado = db.query(Remanejamento).filter(
            Remanejamento.eletricista_id == eletricista_id,
            Remanejamento.data == hoje,
            Remanejamento.supervisor_destino == usuario.base_responsavel
        ).first()
        
        if ja_remanejado:
            return JSONResponse({
                "success": False,
                "erro": "Eletricista já foi remanejado hoje para sua supervisão"
            })
        
        # Criar remanejamento
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
            "mensagem": f"Eletricista {eletricista.colaborador} remanejado com sucesso!"
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
    eletricista_id: int = Form(...),
    prefixo: str = Form(...),
    motivo_id: int = Form(...),
    observacoes: str = Form(""),
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
        # Validar eletricista
        eletricista = db.query(EstruturaEquipes).filter(
            EstruturaEquipes.id == eletricista_id
        ).first()
        
        if not eletricista:
            return JSONResponse({"success": False, "erro": "Eletricista não encontrado"})
        
        # Validar motivo
        motivo = db.query(MotivoIndisponibilidade).filter(
            MotivoIndisponibilidade.id == motivo_id
        ).first()
        
        if not motivo:
            return JSONResponse({"success": False, "erro": "Motivo inválido"})
        
        # Criar indisponibilidade
        hoje = date.today()
        
        nova_indisponibilidade = Indisponibilidade(
            data=hoje,
            eletricista_id=eletricista_id,
            matricula=eletricista.matricula,
            prefixo=prefixo,
            motivo_id=motivo_id,
            observacao=observacoes if observacoes else None,
            usuario_registro=usuario.id
        )
        
        db.add(nova_indisponibilidade)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "mensagem": f"Indisponibilidade de {eletricista.colaborador} registrada com sucesso!"
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
def buscar_eletricistas(q: str = "", db: Session = Depends(get_db)):
    """
    API para buscar eletricistas por nome.
    Retorna JSON com lista de eletricistas que correspondem à busca.
    """
    from models import EstruturaEquipes
    
    # Verificar se tem termo de busca
    if not q or len(q) < 3:
        return JSONResponse({"eletricistas": []})
    
    # Buscar eletricistas (case-insensitive)
    eletricistas = db.query(EstruturaEquipes).filter(
        EstruturaEquipes.colaborador.ilike(f"%{q}%")
    ).limit(10).all()
    
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


# ========================================
# ROTA DE DEBUG
# ========================================

@app.get("/debug-sessao", response_class=HTMLResponse)
def debug_sessao(request: Request):
    """Página de debug para visualizar dados da sessão."""
    
    logado = verificar_autenticacao(request)
    
    session_data = {
        'user_id': request.session.get('user_id'),
        'user_nome': request.session.get('user_nome'),
        'user_perfil': request.session.get('user_perfil'),
        'user_base': request.session.get('user_base')
    }
    
    return templates.TemplateResponse(
        "debug_sessao.html",
        {
            "request": request,
            "logado": logado,
            "session_data": session_data
        }
    )


# ========================================
# EXECUTAR SERVIDOR
# ========================================

if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
