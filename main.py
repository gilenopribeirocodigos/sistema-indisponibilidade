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
    from datetime import datetime
    
    try:
        # Ler JSON do body
        body = await request.json()
        associacoes = body.get('associacoes', [])
        data_registro = body.get('data', None)
        
        if not associacoes:
            return JSONResponse({"success": False, "erro": "Nenhuma associação enviada"})
        
        # Definir data (hoje ou data informada)
        if data_registro:
            try:
                data_obj = datetime.strptime(data_registro, '%Y-%m-%d').date()
            except:
                data_obj = date.today()
        else:
            data_obj = date.today()
        
        # Salvar cada associação
        total_salvo = 0
        for assoc in associacoes:
            nova_equipe = EquipeDia(
                eletricista_id=assoc['eletricista_id'],
                prefixo=assoc['prefixo'],
                data=data_obj,
                supervisor_registro=usuario.base_responsavel or usuario.nome,
                usuario_registro=usuario.id  # ← ADICIONAR ESTA LINHA
            )
            db.add(nova_equipe)
            total_salvo += 1
        
        db.commit()
        
        return JSONResponse({
            "success": True,
            "total": total_salvo,
            "data": data_obj.strftime('%d/%m/%Y'),
            "mensagem": f"{total_salvo} associação(ões) salva(s) para {data_obj.strftime('%d/%m/%Y')}!"
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
    
    from models import Indisponibilidade, EstruturaEquipes, MotivoIndisponibilidade, EquipeDia
    from datetime import datetime
    
    try:
        # Ler dados do formulário
        form_data = await request.form()
        
        eletricista_id = form_data.get('eletricista_id')
        prefixo = form_data.get('prefixo')
        tipo_indisponibilidade = form_data.get('tipo_indisponibilidade')  # ← ADICIONAR
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

        # Verificar se já foi registrado na FREQUÊNCIA hoje
        ja_na_frequencia = db.query(EquipeDia).filter(
            EquipeDia.eletricista_id == eletricista_id,
            EquipeDia.data == data_obj
        ).first()
        
        if ja_na_frequencia:
            return JSONResponse({
                "success": False,
                "erro": f"❌ {eletricista.colaborador} já foi registrado na FREQUÊNCIA hoje! Não pode ser marcado como indisponível."
            })
        
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
            tipo_indisponibilidade=tipo_indisponibilidade,  # ← ADICIONAR
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
    from datetime import datetime
    
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
        EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])  # ← ADICIONAR FILTRO
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
    from datetime import datetime
    
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
        EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])  # ← ADICIONAR FILTRO
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
    """Importar eletricistas de arquivo CSV com UPSERT (preserva IDs)"""
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
        
        # Contadores
        total_novos = 0
        total_atualizados = 0
        
        for row in csv_reader:
            matricula = str(row.get('matricula', '')).strip()
            colaborador = str(row.get('colaborador', '')).strip()
            
            if not matricula or not colaborador:
                continue  # Pula linhas inválidas
            
            # Buscar se já existe no banco (pela matrícula)
            eletricista_existente = db.query(EstruturaEquipes).filter(
                EstruturaEquipes.matricula == matricula
            ).first()
            
            if eletricista_existente:
                # ✅ ATUALIZAR (mantém o ID)
                eletricista_existente.colaborador = colaborador
                eletricista_existente.prefixo = str(row.get('prefixo', '')).strip()
                eletricista_existente.base = str(row.get('base', '')).strip()
                eletricista_existente.polo = str(row.get('polo', '')).strip()
                eletricista_existente.regional = str(row.get('regional', '')).strip()
                eletricista_existente.superv_campo = str(row.get('superv_campo', '')).strip()
                eletricista_existente.superv_operacao = str(row.get('superv_operacao', '')).strip()
                eletricista_existente.coordenador = str(row.get('coordenador', '')).strip()
                eletricista_existente.descr_secao = str(row.get('descr_secao', '')).strip()
                eletricista_existente.descr_situacao = str(row.get('descr_situacao', '')).strip()  # ← ATUALIZA STATUS
                eletricista_existente.placas = str(row.get('placas', '')).strip()
                eletricista_existente.tipo_equipe = str(row.get('tipo_equipe', '')).strip()
                eletricista_existente.processo_equipe = str(row.get('processo_equipe', '')).strip()
                
                total_atualizados += 1
            else:
                # ✅ INSERIR NOVO
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
                    descr_situacao=str(row.get('descr_situacao', '')).strip(),  # ← STATUS DO CSV
                    placas=str(row.get('placas', '')).strip(),
                    tipo_equipe=str(row.get('tipo_equipe', '')).strip(),
                    processo_equipe=str(row.get('processo_equipe', '')).strip()
                )
                db.add(novo_eletricista)
                total_novos += 1
        
        # Commit
        db.commit()
        
        return JSONResponse({
            "success": True,
            "total_novos": total_novos,
            "total_atualizados": total_atualizados,
            "mensagem": f"✅ Importação concluída! {total_novos} novos, {total_atualizados} atualizados."
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
# ROTAS DE GESTÃO DE USUÁRIOS
# ========================================

@app.get("/usuarios", response_class=HTMLResponse)
def listar_usuarios(request: Request, db: Session = Depends(get_db)):
    """Listar todos os usuários (apenas ADMIN)"""
    
    # Verificar se está logado
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    # Verificar se é ADMIN
    if usuario.perfil != 'admin':
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "usuario": usuario,
                "erro": "⚠️ Acesso negado! Apenas administradores podem gerenciar usuários."
            }
        )
    
    # Buscar todos os usuários
    usuarios = db.query(Usuario).order_by(Usuario.nome).all()
    
    return templates.TemplateResponse(
        "usuarios.html",
        {
            "request": request,
            "usuario": usuario,
            "usuarios": usuarios
        }
    )


@app.get("/usuarios/novo", response_class=HTMLResponse)
def novo_usuario_page(request: Request, db: Session = Depends(get_db)):
    """Página para criar novo usuário"""
    
    # Verificar se está logado
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    # Verificar se é ADMIN
    if usuario.perfil != 'admin':
        return RedirectResponse(url="/usuarios")
    
    # Buscar supervisores únicos da tabela estrutura_equipes
    from models import EstruturaEquipes
    supervisores = db.query(EstruturaEquipes.superv_campo).distinct().all()
    supervisores = [s[0] for s in supervisores if s[0]]
    supervisores.append("Todas")
    
    return templates.TemplateResponse(
        "usuario_form.html",
        {
            "request": request,
            "usuario": usuario,
            "supervisores": supervisores,
            "usuario_edicao": None
        }
    )


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
    """Criar novo usuário"""
    
    # Verificar se está logado
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario_logado = get_usuario_logado(request, db)
    if not usuario_logado or usuario_logado.perfil != 'admin':
        return RedirectResponse(url="/usuarios")
    
    from auth import criar_hash_senha
    from models import EstruturaEquipes
    
    try:
        # Verificar se login já existe
        existe = db.query(Usuario).filter(Usuario.login == login).first()
        if existe:
            supervisores = db.query(EstruturaEquipes.superv_campo).distinct().all()
            supervisores = [s[0] for s in supervisores if s[0]]
            supervisores.append("Todas")
            
            return templates.TemplateResponse(
                "usuario_form.html",
                {
                    "request": request,
                    "usuario": usuario_logado,
                    "supervisores": supervisores,
                    "usuario_edicao": None,
                    "erro": f"❌ Login '{login}' já existe! Escolha outro."
                }
            )
        
        # Criar novo usuário
        novo_usuario = Usuario(
            nome=nome,
            login=login,
            senha_hash=criar_hash_senha(senha),
            perfil=perfil,
            base_responsavel=base_responsavel if base_responsavel else None,
            ativo=ativo
        )
        
        db.add(novo_usuario)
        db.commit()
        
        # Redirecionar com sucesso
        return RedirectResponse(
            url=f"/usuarios?sucesso=Usuário '{nome}' criado com sucesso!",
            status_code=302
        )
        
    except Exception as e:
        db.rollback()
        
        supervisores = db.query(EstruturaEquipes.superv_campo).distinct().all()
        supervisores = [s[0] for s in supervisores if s[0]]
        supervisores.append("Todas")
        
        return templates.TemplateResponse(
            "usuario_form.html",
            {
                "request": request,
                "usuario": usuario_logado,
                "supervisores": supervisores,
                "usuario_edicao": None,
                "erro": f"❌ Erro ao criar usuário: {str(e)}"
            }
        )


@app.get("/usuarios/editar/{user_id}", response_class=HTMLResponse)
def editar_usuario_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Página para editar usuário"""
    
    # Verificar se está logado
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    # Verificar se é ADMIN
    if usuario.perfil != 'admin':
        return RedirectResponse(url="/usuarios")
    
    # Buscar usuário a ser editado
    usuario_edicao = db.query(Usuario).filter(Usuario.id == user_id).first()
    
    if not usuario_edicao:
        return RedirectResponse(url="/usuarios?erro=Usuário não encontrado!")
    
    # Buscar supervisores
    from models import EstruturaEquipes
    supervisores = db.query(EstruturaEquipes.superv_campo).distinct().all()
    supervisores = [s[0] for s in supervisores if s[0]]
    supervisores.append("Todas")
    
    return templates.TemplateResponse(
        "usuario_form.html",
        {
            "request": request,
            "usuario": usuario,
            "supervisores": supervisores,
            "usuario_edicao": usuario_edicao
        }
    )


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
    """Salvar edição de usuário"""
    
    # Verificar se está logado
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario_logado = get_usuario_logado(request, db)
    if not usuario_logado or usuario_logado.perfil != 'admin':
        return RedirectResponse(url="/usuarios")
    
    try:
        # Buscar usuário
        usuario_edicao = db.query(Usuario).filter(Usuario.id == user_id).first()
        
        if not usuario_edicao:
            return RedirectResponse(url="/usuarios?erro=Usuário não encontrado!")
        
        # Atualizar dados
        usuario_edicao.nome = nome
        usuario_edicao.perfil = perfil
        usuario_edicao.base_responsavel = base_responsavel if base_responsavel else None
        usuario_edicao.ativo = ativo
        
        db.commit()
        
        # Redirecionar com sucesso
        return RedirectResponse(
            url=f"/usuarios?sucesso=Usuário '{nome}' atualizado com sucesso!",
            status_code=302
        )
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(
            url=f"/usuarios?erro=Erro ao atualizar usuário: {str(e)}",
            status_code=302
        )


# ========================================
# APIs DE GESTÃO DE USUÁRIOS
# ========================================

@app.post("/api/usuarios/toggle-status")
async def toggle_status_usuario(request: Request, db: Session = Depends(get_db)):
    """Ativar/Desativar usuário"""
    
    # Verificar autenticação
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario_logado = get_usuario_logado(request, db)
    if not usuario_logado or usuario_logado.perfil != 'admin':
        return JSONResponse({"success": False, "erro": "Acesso negado"})
    
    try:
        body = await request.json()
        user_id = body.get('user_id')
        ativo = body.get('ativo')
        
        # Buscar usuário
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        
        if not usuario:
            return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
        
        # Não permitir desativar o próprio usuário
        if usuario.id == usuario_logado.id:
            return JSONResponse({"success": False, "erro": "Você não pode desativar sua própria conta!"})
        
        # Atualizar status
        usuario.ativo = ativo
        db.commit()
        
        acao = "ativado" if ativo else "desativado"
        
        return JSONResponse({
            "success": True,
            "mensagem": f"Usuário '{usuario.nome}' {acao} com sucesso!"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({"success": False, "erro": str(e)})


@app.post("/api/usuarios/resetar-senha")
async def resetar_senha_usuario(request: Request, db: Session = Depends(get_db)):
    """Resetar senha de usuário"""
    
    # Verificar autenticação
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
        
        # Buscar usuário
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        
        if not usuario:
            return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
        
        # Atualizar senha
        usuario.senha_hash = criar_hash_senha(nova_senha)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "mensagem": f"Senha de '{usuario.nome}' resetada com sucesso!"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({"success": False, "erro": str(e)})

# ========================================
# ROTAS DE RELATÓRIOS
# ========================================

@app.get("/relatorios", response_class=HTMLResponse)
def relatorios_page(request: Request, db: Session = Depends(get_db)):
    """Página de relatórios"""
    
    # Verificar se está logado
    if not verificar_autenticacao(request):
        return RedirectResponse(url="/login")
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    from models import EstruturaEquipes
    from datetime import datetime, timedelta
    
    # Buscar supervisores únicos
    supervisores = db.query(EstruturaEquipes.superv_campo).distinct().all()
    supervisores = [s[0] for s in supervisores if s[0]]
    
    # Datas padrão
    hoje = date.today()
    inicio_mes = date(hoje.year, hoje.month, 1)
    
    return templates.TemplateResponse(
        "relatorios.html",
        {
            "request": request,
            "usuario": usuario,
            "supervisores": supervisores,
            "hoje_iso": hoje.isoformat(),
            "inicio_mes": inicio_mes.isoformat()
        }
    )


@app.get("/api/relatorio-geral")
def relatorio_geral(
    request: Request,
    data_inicio: str = None,
    data_fim: str = None,
    db: Session = Depends(get_db)
):
    """API para gerar relatório GERAL (consolidado de todos)"""
    
    # Verificar autenticação
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import EstruturaEquipes, EquipeDia, Indisponibilidade, MotivoIndisponibilidade
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    try:
        # Definir período
        if data_inicio and data_fim:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        elif data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = data_inicio_obj
        else:
            data_inicio_obj = date.today()
            data_fim_obj = date.today()
        
        # Buscar total de eletricistas ATIVOS/RESERVA
        total_eletricistas = db.query(EstruturaEquipes).filter(
            EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])
        ).count()
        
        # Criar lista de datas no período
        dias_periodo = []
        data_atual = data_inicio_obj
        while data_atual <= data_fim_obj:
            dias_periodo.append(data_atual)
            data_atual += timedelta(days=1)
        
        # Dicionário para contar
        resultado = {
            "Presente": 0,
            "Não registrado": 0
        }
        
        # Para cada dia no período
        for dia in dias_periodo:
            # 1. PRESENTES (frequência)
            ids_presentes = db.query(EquipeDia.eletricista_id).filter(
                EquipeDia.data == dia
            ).all()
            ids_presentes = set([p[0] for p in ids_presentes])
            
            resultado["Presente"] += len(ids_presentes)
            
            # 2. INDISPONÍVEIS com motivo
            indisponiveis = db.query(
                Indisponibilidade.eletricista_id,
                MotivoIndisponibilidade.descricao
            ).join(
                MotivoIndisponibilidade,
                Indisponibilidade.motivo_id == MotivoIndisponibilidade.id
            ).filter(
                Indisponibilidade.data == dia
            ).all()
            
            ids_indisponiveis = set([i[0] for i in indisponiveis])
            
            # Contar por motivo
            for elet_id, motivo in indisponiveis:
                if motivo not in resultado:
                    resultado[motivo] = 0
                resultado[motivo] += 1
            
            # 3. NÃO REGISTRADOS
            ids_registrados = ids_presentes.union(ids_indisponiveis)
            
            total_nao_registrados = db.query(EstruturaEquipes.id).filter(
                EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA']),
                ~EstruturaEquipes.id.in_(list(ids_registrados))
            ).count()
            
            resultado["Não registrado"] += total_nao_registrados
        
        # Calcular total de registros
        total_registros = sum(resultado.values())
        
        # Calcular percentuais
        dados_relatorio = []
        for motivo, qtde in resultado.items():
            percentual = (qtde / total_registros * 100) if total_registros > 0 else 0
            dados_relatorio.append({
                "motivo": motivo,
                "qtde": qtde,
                "percentual": round(percentual, 1)
            })
        
        # Ordenar: Presente primeiro, depois alfabético
        dados_relatorio.sort(key=lambda x: (
            0 if x['motivo'] == 'Presente' else 
            2 if x['motivo'] == 'Não registrado' else 
            1,
            x['motivo']
        ))
        
        return JSONResponse({
            "success": True,
            "periodo": {
                "inicio": data_inicio_obj.strftime('%d/%m/%Y'),
                "fim": data_fim_obj.strftime('%d/%m/%Y'),
                "dias": len(dias_periodo)
            },
            "total_eletricistas": total_eletricistas,
            "total_registros": total_registros,
            "dados": dados_relatorio
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "erro": str(e)
        })


# FUNÇÃO CORRIGIDA COM DEBUG
# Substitua a função relatorio_por_supervisor no main.py pela versão abaixo

@app.get("/api/relatorio-por-supervisor")
def relatorio_por_supervisor(
    request: Request,
    data_inicio: str = None,
    data_fim: str = None,
    db: Session = Depends(get_db)
):
    """API para gerar relatório POR SUPERVISOR - COM DEBUG"""
    
    # Verificar autenticação
    if not verificar_autenticacao(request):
        return JSONResponse({"success": False, "erro": "Não autenticado"})
    
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return JSONResponse({"success": False, "erro": "Usuário não encontrado"})
    
    from models import EstruturaEquipes, EquipeDia, Indisponibilidade, MotivoIndisponibilidade
    from datetime import datetime, timedelta
    
    try:
        # Definir período
        if data_inicio and data_fim:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        elif data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = data_inicio_obj
        else:
            data_inicio_obj = date.today()
            data_fim_obj = date.today()
        
        print(f"\n{'='*60}")
        print(f"DEBUG RELATÓRIO - Período: {data_inicio_obj} até {data_fim_obj}")
        print(f"{'='*60}")
        
        # Criar lista de datas no período
        dias_periodo = []
        data_atual = data_inicio_obj
        while data_atual <= data_fim_obj:
            dias_periodo.append(data_atual)
            data_atual += timedelta(days=1)
        
        print(f"Total de dias no período: {len(dias_periodo)}")
        
        # Buscar todos os supervisores
        supervisores = db.query(EstruturaEquipes.superv_campo).filter(
            EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])
        ).distinct().all()
        supervisores = [s[0] for s in supervisores if s[0]]
        
        print(f"Total de supervisores: {len(supervisores)}")
        
        # Buscar todos os motivos possíveis
        motivos_db = db.query(MotivoIndisponibilidade.descricao).all()
        todos_motivos = set([m[0] for m in motivos_db])
        
        print(f"Motivos cadastrados: {list(todos_motivos)}")
        
        # TESTE: Verificar se há indisponibilidades no período
        total_indisp_periodo = db.query(Indisponibilidade).filter(
            Indisponibilidade.data >= data_inicio_obj,
            Indisponibilidade.data <= data_fim_obj
        ).count()
        print(f"Total de indisponibilidades no período: {total_indisp_periodo}")
        
        if total_indisp_periodo > 0:
            # Mostrar exemplos
            exemplos = db.query(
                Indisponibilidade.data,
                Indisponibilidade.eletricista_id,
                MotivoIndisponibilidade.descricao
            ).join(
                MotivoIndisponibilidade,
                Indisponibilidade.motivo_id == MotivoIndisponibilidade.id
            ).filter(
                Indisponibilidade.data >= data_inicio_obj,
                Indisponibilidade.data <= data_fim_obj
            ).limit(5).all()
            
            print("\nExemplos de indisponibilidades no período:")
            for data, elet_id, motivo in exemplos:
                print(f"  - Data: {data}, Eletricista ID: {elet_id}, Motivo: {motivo}")
        
        dados_supervisores = []
        
        # Para cada supervisor
        for supervisor in supervisores:
            print(f"\n--- Supervisor: {supervisor} ---")
            
            # Total de eletricistas desse supervisor
            total_eletricistas_sup = db.query(EstruturaEquipes).filter(
                EstruturaEquipes.superv_campo == supervisor,
                EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA'])
            ).count()
            
            print(f"Total de eletricistas: {total_eletricistas_sup}")
            
            # Contadores por motivo
            contadores = {
                "Presente": 0,
                "Não registrado": 0
            }
            
            # Para cada dia
            for dia in dias_periodo:
                # 1. PRESENTES
                presentes = db.query(EquipeDia.eletricista_id).join(
                    EstruturaEquipes,
                    EquipeDia.eletricista_id == EstruturaEquipes.id
                ).filter(
                    EquipeDia.data == dia,
                    EstruturaEquipes.superv_campo == supervisor
                ).all()
                
                ids_presentes = set([p[0] for p in presentes])
                contadores["Presente"] += len(ids_presentes)
                
                # 2. INDISPONÍVEIS - COM DEBUG
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
                    Indisponibilidade.data == dia,
                    EstruturaEquipes.superv_campo == supervisor
                ).all()
                
                if indisponiveis:
                    print(f"  Dia {dia}: Encontrados {len(indisponiveis)} indisponíveis")
                    for elet_id, motivo in indisponiveis:
                        print(f"    - Eletricista ID: {elet_id}, Motivo: '{motivo}'")
                
                ids_indisponiveis = set([i[0] for i in indisponiveis])
                
                for elet_id, motivo in indisponiveis:
                    if motivo not in contadores:
                        contadores[motivo] = 0
                    contadores[motivo] += 1
                
                # 3. NÃO REGISTRADOS
                ids_registrados = ids_presentes.union(ids_indisponiveis)
                
                nao_registrados = db.query(EstruturaEquipes.id).filter(
                    EstruturaEquipes.superv_campo == supervisor,
                    EstruturaEquipes.descr_situacao.in_(['ATIVO', 'RESERVA']),
                    ~EstruturaEquipes.id.in_(list(ids_registrados)) if ids_registrados else True
                ).count()
                
                contadores["Não registrado"] += nao_registrados
            
            print(f"Contadores finais: {contadores}")
            
            # Calcular totais
            total_registros = sum(contadores.values())
            percentual_presenca = (contadores["Presente"] / total_registros * 100) if total_registros > 0 else 0
            
            dados_supervisores.append({
                "supervisor": supervisor,
                "total_eletricistas": total_eletricistas_sup,
                "contadores": contadores,
                "total_registros": total_registros,
                "percentual_presenca": round(percentual_presenca, 1)
            })
        
        # Ordenar por % de presença (decrescente)
        dados_supervisores.sort(key=lambda x: x['percentual_presenca'], reverse=True)
        
        # Calcular totais gerais
        total_geral = sum([s['total_registros'] for s in dados_supervisores])
        
        print(f"\n{'='*60}")
        print(f"TOTAL GERAL: {total_geral}")
        print(f"{'='*60}\n")
        
        return JSONResponse({
            "success": True,
            "periodo": {
                "inicio": data_inicio_obj.strftime('%d/%m/%Y'),
                "fim": data_fim_obj.strftime('%d/%m/%Y'),
                "dias": len(dias_periodo)
            },
            "todos_motivos": sorted(list(todos_motivos)),
            "dados": dados_supervisores,
            "total_geral": total_geral
        })
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse({
            "success": False,
            "erro": str(e)
        })

# ========================================
# EXECUTAR SERVIDOR
# ========================================

if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)

