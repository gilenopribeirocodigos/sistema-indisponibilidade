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
    from datetime import datetime
    
    # Definir data (hoje ou data selecionada)
    if data:
        try:
            data_selecionada = datetime.strptime(data, '%Y-%m-%d').date()
        except:
            data_selecionada = date.today()
    else:
        data_selecionada = date.today()
    
    # Buscar IDs dos eletricistas já registrados na data selecionada
    eletricistas_ja_registrados = db.query(EquipeDia.eletricista_id).filter(
        EquipeDia.data == data_selecionada
    ).all()
    
    ids_ja_registrados = [e[0] for e in eletricistas_ja_registrados]
    
    # Buscar eletricistas
    supervisor_campo = usuario.base_responsavel
    
    # Criar query base
    query = db.query(EstruturaEquipes)
    
    # EXCLUIR eletricistas já registrados na data selecionada
    if ids_ja_registrados:
        query = query.filter(~EstruturaEquipes.id.in_(ids_ja_registrados))
    
    # Se for ADMIN ou base "Todas", mostra TODOS (que ainda não foram registrados)
    if not supervisor_campo or supervisor_campo.upper() == "TODAS":
        eletricistas = query.order_by(EstruturaEquipes.colaborador).all()
        
        # Buscar todos os prefixos únicos
        prefixos_supervisor = db.query(EstruturaEquipes.prefixo).distinct().all()
    else:
        # Senão, filtra pela supervisão específica
        eletricistas = query.filter(
            EstruturaEquipes.superv_campo == supervisor_campo
        ).order_by(EstruturaEquipes.colaborador).all()
        
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
            "eletricistas": eletricistas,
            "prefixos_supervisor": prefixos_supervisor,
            "motivos": motivos,
            "hoje": hoje_formatado,
            "hoje_iso": hoje_iso,
            "data_selecionada": data_selecionada_iso,
            "data_selecionada_formatada": data_selecionada_formatada
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
# ROTA DE IMPORTAÇÃO CSV
# ========================================

from fastapi import UploadFile, File

@app.get("/importar-csv", response_class=HTMLResponse)
def importar_csv_page(request: Request, db: Session = Depends(get_db)):
    """Página de importação de CSV"""
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("importar_csv.html", {"request": request, "usuario": usuario})

@app.post("/api/importar-eletricistas")
async def importar_eletricistas(request: Request, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    """Importar eletricistas de arquivo CSV"""
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    from models import EstruturaEquipes
    import csv
    import io
    
    try:
        # Ler arquivo
        contents = await arquivo.read()
        
        # Tentar UTF-8, se falhar tenta Latin-1
        try:
            decoded = contents.decode('utf-8')
        except:
            decoded = contents.decode('latin-1')
        
        # Ler CSV
        csv_reader = csv.DictReader(io.StringIO(decoded), delimiter=';')
        
        # LIMPAR TABELA ANTES (CUIDADO!)
        db.query(EstruturaEquipes).delete()
        db.commit()
        
        total = 0
        batch = []
        
        for row in csv_reader:
            matricula = str(row.get('matricula', '')).strip()
            colaborador = str(row.get('colaborador', '')).strip()
            
            if matricula and colaborador:
                obj = EstruturaEquipes(
                    colaborador=colaborador,
                    matricula=matricula,
                    prefixo=str(row.get('prefixo', '')).strip(),
                    base=str(row.get('base', '')).strip(),
                    polo=str(row.get('polo', '')).strip(),
                    regional=str(row.get('regional', '')).strip(),
                    superv_campo=str(row.get('superv_campo', '')).strip()
                )
                batch.append(obj)
                total += 1
                
                # Inserir em lotes de 50
                if len(batch) >= 50:
                    db.bulk_save_objects(batch)
                    db.commit()
                    batch = []
        
        # Inserir restante
        if batch:
            db.bulk_save_objects(batch)
            db.commit()
        
        return JSONResponse({
            "success": True,
            "total_novos": total,
            "total_atualizados": 0,
            "mensagem": f"✅ {total} eletricistas importados!"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "erro": f"Erro: {str(e)}"
        })

@app.get("/api/teste-eletricistas")
def teste_eletricistas(db: Session = Depends(get_db)):
    """Rota de teste para ver quantos eletricistas existem"""
    from models import EstruturaEquipes
    
    try:
        total = db.query(EstruturaEquipes).count()
        todos = db.query(EstruturaEquipes).limit(5).all()
        
        resultado = []
        for e in todos:
            resultado.append({
                "id": e.id,
                "colaborador": e.colaborador,
                "matricula": e.matricula,
                "prefixo": e.prefixo
            })
        
        return JSONResponse({
            "total_no_banco": total,
            "primeiros_5": resultado
        })
    except Exception as e:
        return JSONResponse({"erro": str(e)})

@app.get("/api/listar-todos-eletricistas")
def listar_todos_eletricistas(request: Request, db: Session = Depends(get_db)):
    """Listar TODOS os eletricistas sem filtro"""
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    from models import EstruturaEquipes
    
    try:
        eletricistas = db.query(EstruturaEquipes).all()
        
        resultado = []
        for e in eletricistas:
            resultado.append({
                "id": e.id,
                "colaborador": e.colaborador,
                "matricula": e.matricula,
                "prefixo": e.prefixo,
                "base": e.base,
                "polo": e.polo,
                "regional": e.regional,
                "superv_campo": e.superv_campo
            })
        
        return JSONResponse({
            "success": True,
            "total": len(resultado),
            "eletricistas": resultado
        })
    except Exception as e:
        return JSONResponse({"success": False, "erro": str(e)})

@app.get("/api/teste-motivos")
def teste_motivos(db: Session = Depends(get_db)):
    """Rota de teste para ver motivos"""
    from models import MotivoIndisponibilidade
    
    try:
        motivos = db.query(MotivoIndisponibilidade).all()
        
        resultado = []
        for m in motivos:
            resultado.append({
                "id": m.id,
                "descricao": m.descricao,
                "ativo": m.ativo
            })
        
        return JSONResponse({
            "total": len(resultado),
            "motivos": resultado
        })
    except Exception as e:
        return JSONResponse({"erro": str(e)})
        
@app.get("/api/criar-motivos-padrao")
def criar_motivos_padrao(db: Session = Depends(get_db)):
    """Criar motivos padrão de indisponibilidade"""
    from models import MotivoIndisponibilidade
    
    motivos_corretos = [
        "ATESTADO MEDICO",
        "FALTA INJUSTIFICADA",
        "VIATURA COM DEFEITO",
        "VIATURA EM MANUTENCAO",
        "ACIDENTE",
        "TREINAMENTO",
        "FERIAS",
        "LICENCA",
        "OUTRO"
    ]
    
    try:
        total_criado = 0
        
        for descricao in motivos_corretos:
            # Verificar se já existe
            existe = db.query(MotivoIndisponibilidade).filter(
                MotivoIndisponibilidade.descricao == descricao
            ).first()
            
            if not existe:
                novo_motivo = MotivoIndisponibilidade(
                    descricao=descricao,
                    ativo=True
                )
                db.add(novo_motivo)
                total_criado += 1
        
        db.commit()
        
        return JSONResponse({
            "success": True,
            "total_criado": total_criado,
            "mensagem": f"✅ {total_criado} motivos criados com sucesso!"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "erro": str(e)
        })

# ========================================
# EXECUTAR SERVIDOR
# ========================================

if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)















