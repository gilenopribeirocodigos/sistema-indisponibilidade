// ==========================================
// REGISTRO V2 - INTERFACE DINÂMICA
// ==========================================

class RegistroV2 {
    constructor() {
        this.associacoesTemporarias = [];
        this.init();
    }
    
    init() {
        this.setupTipoSelector();
        this.setupFrequencia();
        this.setupRemanejado();
        this.setupIndisponivel();
    }
    
    // ==========================================
    // CONTROLE DE SEÇÕES (3 botões)
    // ==========================================
    setupTipoSelector() {
        const botoes = document.querySelectorAll('.tipo-btn');
        const secoes = document.querySelectorAll('.secao-operacao');
        
        botoes.forEach(botao => {
            botao.addEventListener('click', () => {
                const tipo = botao.dataset.tipo;
                
                // Remover active de todos
                botoes.forEach(b => b.classList.remove('active'));
                secoes.forEach(s => s.classList.remove('active'));
                
                // Adicionar active no selecionado
                botao.classList.add('active');
                document.getElementById(`secao-${tipo}`).classList.add('active');
            });
        });
    }    
    
    // ==========================================
    // SEÇÃO 1: FREQUÊNCIA - PRESENÇA/AUSÊNCIA
    // ==========================================
    setupFrequencia() {
        const checkboxes = document.querySelectorAll('.eletricista-checkbox');
        const eletricistagInfo = document.getElementById('eletricista-info');
        const contadorSelecao = document.getElementById('contador-selecao');
        const hintSelecao = document.getElementById('hint-selecao');
        
        // ✅ ELEMENTOS PRESENÇA
        const prefixoInput = document.getElementById('prefixo-frequencia');
        const btnAssociar = document.getElementById('btn-associar');
        const painelPresenca = document.getElementById('painel-presenca');
        
        // ✅ ELEMENTOS AUSÊNCIA
        const motivoSelect = document.getElementById('motivo-ausencia');
        const btnRegistrarAusencia = document.getElementById('btn-registrar-ausencia');
        const painelAusencia = document.getElementById('painel-ausencia');
        
        // ✅ RADIO BUTTONS
        const radioPresenca = document.querySelector('input[name="tipo-registro"][value="presenca"]');
        const radioAusencia = document.querySelector('input[name="tipo-registro"][value="ausencia"]');
        
        const btnSalvarFrequencia = document.getElementById('btn-salvar-frequencia');
        const btnLimparTodas = document.getElementById('btn-limpar-todas');
        
        let eletricistaSelecionados = [];
        let modoAtual = 'presenca'; // 'presenca' ou 'ausencia'
        let limiteSelecao = 2; // 2 para presença, 1 para ausência
        
        // ✅ CARREGAR MOTIVOS DE AUSÊNCIA
        const carregarMotivos = async () => {
            try {
                const response = await fetch('/api/motivos-indisponibilidade');
                const data = await response.json();
                
                if (data.success) {
                    motivoSelect.innerHTML = '<option value="">Selecione o motivo...</option>';
                    data.motivos.forEach(motivo => {
                        motivoSelect.innerHTML += `<option value="${motivo.id}">${motivo.descricao}</option>`;
                    });
                }
            } catch (error) {
                console.error('Erro ao carregar motivos:', error);
            }
        };
        
        // Carregar motivos ao iniciar
        carregarMotivos();
        
        // ✅ ALTERNAR ENTRE PRESENÇA/AUSÊNCIA
        const alternarModo = (novoModo) => {
            modoAtual = novoModo;
            
            if (novoModo === 'presenca') {
                limiteSelecao = 2;
                painelPresenca.style.display = 'block';
                painelAusencia.style.display = 'none';
                contadorSelecao.textContent = '0/2';
                hintSelecao.textContent = 'Selecione até 2 eletricistas e associe ao prefixo';
            } else {
                limiteSelecao = 1;
                painelPresenca.style.display = 'none';
                painelAusencia.style.display = 'block';
                contadorSelecao.textContent = '0/1';
                hintSelecao.textContent = 'Selecione 1 eletricista e informe o motivo da ausência';
            }
            
            // Limpar seleções ao trocar de modo
            checkboxes.forEach(cb => {
                cb.checked = false;
                cb.disabled = false;
                cb.closest('.eletricista-card').style.opacity = '1';
            });
            
            eletricistaSelecionados = [];
            atualizarInterface();
        };
        
        // Eventos dos radio buttons
        radioPresenca.addEventListener('change', () => alternarModo('presenca'));
        radioAusencia.addEventListener('change', () => alternarModo('ausencia'));
        
        // ✅ ATUALIZAR INTERFACE
        const atualizarInterface = () => {
            const qtdSelecionados = eletricistaSelecionados.length;
            
            // Atualizar contador
            contadorSelecao.textContent = `${qtdSelecionados}/${limiteSelecao}`;
            contadorSelecao.className = 'contador-badge';
            if (qtdSelecionados === limiteSelecao) {
                contadorSelecao.classList.add('contador-completo');
            } else if (qtdSelecionados > 0) {
                contadorSelecao.classList.add('contador-parcial');
            }
            
            // Desabilitar checkboxes se atingiu limite
            checkboxes.forEach(cb => {
                if (!cb.checked && qtdSelecionados >= limiteSelecao) {
                    cb.disabled = true;
                    cb.closest('.eletricista-card').style.opacity = '0.5';
                } else if (!cb.checked) {
                    cb.disabled = false;
                    cb.closest('.eletricista-card').style.opacity = '1';
                }
            });
            
            // Atualizar painel de informações
            if (qtdSelecionados === 0) {
                eletricistagInfo.innerHTML = `Selecione até ${limiteSelecao} eletricista(s) acima`;
                eletricistagInfo.classList.remove('info-preenchida');
                eletricistagInfo.classList.add('info-vazia');
                
                if (modoAtual === 'presenca') {
                    prefixoInput.value = '';
                    btnAssociar.disabled = true;
                } else {
                    motivoSelect.value = '';
                    btnRegistrarAusencia.disabled = true;
                }
            } else {
                const htmlEletricistas = eletricistaSelecionados.map((elet, index) => `
                    <div class="eletricista-selecionado">
                        <strong>${index + 1}. ${elet.nome}</strong><br>
                        <small>Mat: ${elet.matricula} | Base: ${elet.base}</small>
                    </div>
                `).join('');
                
                eletricistagInfo.innerHTML = htmlEletricistas;
                eletricistagInfo.classList.add('info-preenchida');
                eletricistagInfo.classList.remove('info-vazia');
                
                if (modoAtual === 'presenca') {
                    // Sugerir prefixo do primeiro
                    if (!prefixoInput.value) {
                        prefixoInput.value = eletricistaSelecionados[0].prefixo;
                    }
                    btnAssociar.disabled = false;
                } else {
                    btnRegistrarAusencia.disabled = false;
                }
            }
        };
        
        // ✅ CHECKBOXES
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const card = e.target.closest('.eletricista-card');
                const eletData = {
                    id: card.dataset.id,
                    nome: e.target.dataset.nome,
                    matricula: e.target.dataset.matricula,
                    prefixo: e.target.dataset.prefixo,
                    base: e.target.dataset.base
                };
                
                if (e.target.checked) {
                    if (eletricistaSelecionados.length < limiteSelecao) {
                        eletricistaSelecionados.push(eletData);
                    } else {
                        e.target.checked = false;
                        return;
                    }
                } else {
                    eletricistaSelecionados = eletricistaSelecionados.filter(
                        elet => elet.id !== eletData.id
                    );
                }
                
                atualizarInterface();
            });
        });
        
        // ✅ BOTÃO ASSOCIAR (PRESENÇA)
        if (btnAssociar) {
            btnAssociar.addEventListener('click', () => {
                if (eletricistaSelecionados.length === 0) return;
                
                const prefixo = prefixoInput.value.trim();
                
                if (!prefixo) {
                    alert('⚠️ Informe o prefixo da equipe!');
                    prefixoInput.focus();
                    return;
                }
                
                // Adicionar à lista temporária (PRESENÇA)
                eletricistaSelecionados.forEach(eletricista => {
                    const jaAssociado = this.associacoesTemporarias.find(
                        a => a.eletricista_id === eletricista.id
                    );
                    
                    if (!jaAssociado) {
                        this.associacoesTemporarias.push({
                            eletricista_id: eletricista.id,
                            nome: eletricista.nome,
                            matricula: eletricista.matricula,
                            prefixo: prefixo,
                            tipo: 'presenca'  // ✅ Identifica como presença
                        });
                        
                        const card = document.querySelector(`.eletricista-card[data-id="${eletricista.id}"]`);
                        card.style.display = 'none';
                    }
                });
                
                // Limpar seleção
                checkboxes.forEach(cb => {
                    cb.checked = false;
                    cb.disabled = false;
                    cb.closest('.eletricista-card').style.opacity = '1';
                });
                
                eletricistaSelecionados = [];
                atualizarInterface();
                this.atualizarListaAssociacoes();
            });
        }
        
        // ✅ BOTÃO REGISTRAR AUSÊNCIA
        if (btnRegistrarAusencia) {
            btnRegistrarAusencia.addEventListener('click', () => {
                if (eletricistaSelecionados.length === 0) return;
                
                const motivoId = motivoSelect.value;
                const motivoTexto = motivoSelect.options[motivoSelect.selectedIndex]?.text;
                
                if (!motivoId) {
                    alert('⚠️ Selecione o motivo da ausência!');
                    motivoSelect.focus();
                    return;
                }
                
                // Adicionar à lista temporária (AUSÊNCIA)
                const eletricista = eletricistaSelecionados[0];
                
                const jaAssociado = this.associacoesTemporarias.find(
                    a => a.eletricista_id === eletricista.id
                );
                
                if (!jaAssociado) {
                    this.associacoesTemporarias.push({
                        eletricista_id: eletricista.id,
                        nome: eletricista.nome,
                        matricula: eletricista.matricula,
                        prefixo: '-',  // ✅ Sem prefixo para ausências
                        tipo: 'ausencia',  // ✅ Identifica como ausência
                        id_indisponibilidade: parseInt(motivoId),
                        motivo_texto: motivoTexto
                    });
                    
                    const card = document.querySelector(`.eletricista-card[data-id="${eletricista.id}"]`);
                    card.style.display = 'none';
                }
                
                // Limpar seleção
                checkboxes.forEach(cb => {
                    cb.checked = false;
                    cb.disabled = false;
                    cb.closest('.eletricista-card').style.opacity = '1';
                });
                
                eletricistaSelecionados = [];
                motivoSelect.value = '';
                atualizarInterface();
                this.atualizarListaAssociacoes();
            });
        }
        
        // ✅ RESTO DO CÓDIGO (Salvar, Limpar) PERMANECE IGUAL
        
        // Botão Salvar Frequência        
        if (btnSalvarFrequencia) {
            btnSalvarFrequencia.addEventListener('click', async () => {
                if (this.associacoesTemporarias.length === 0) {
                    alert('⚠️ Não há associações para salvar!');
                    return;
                }
                
                if (!confirm(`💾 Salvar ${this.associacoesTemporarias.length} registro(s)?`)) {
                    return;
                }
                
                try {
                    btnSalvarFrequencia.disabled = true;
                    btnSalvarFrequencia.textContent = '⏳ Salvando...';
                    
                    const dataRegistro = document.getElementById('data-registro').value;
                    const associacoesSalvas = [...this.associacoesTemporarias];
                    
                    const response = await fetch('/api/salvar-frequencia', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            associacoes: this.associacoesTemporarias,
                            data: dataRegistro 
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        this.mostrarRegistrosSalvos(associacoesSalvas, result.data);
                        this.associacoesTemporarias = [];
                        this.atualizarListaAssociacoes();
                        document.getElementById('associacoes-temporarias').style.display = 'none';
                    } else {
                        alert(`❌ Erro: ${result.erro}`);
                    }
                    
                } catch (error) {
                    alert('❌ Erro ao salvar: ' + error.message);
                } finally {
                    btnSalvarFrequencia.disabled = false;
                    btnSalvarFrequencia.textContent = '💾 Salvar Todas as Associações';
                }
            });
        }
        
        // Botão Limpar Todas
        if (btnLimparTodas) {
            btnLimparTodas.addEventListener('click', () => {
                if (!confirm('🗑️ Limpar todas as associações pendentes?')) return;
                
                document.querySelectorAll('.eletricista-card').forEach(card => {
                    card.style.display = 'block';
                });
                
                this.associacoesTemporarias = [];
                this.atualizarListaAssociacoes();
            });
        }
    }
    
    ####
    atualizarListaAssociacoes() {
        const container = document.getElementById('associacoes-temporarias');
        const lista = document.getElementById('lista-associacoes');
        
        if (this.associacoesTemporarias.length === 0) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'block';
        
        lista.innerHTML = this.associacoesTemporarias.map((assoc, index) => {
            // ✅ MOSTRAR DIFERENTE PARA PRESENÇA E AUSÊNCIA
            const detalhes = assoc.tipo === 'ausencia' 
                ? `Mat: ${assoc.matricula} → <strong style="color: #dc3545;">AUSENTE</strong> (${assoc.motivo_texto})`
                : `Mat: ${assoc.matricula} → Prefixo: ${assoc.prefixo}`;
            
            const cor = assoc.tipo === 'ausencia' ? '#fff3cd' : '#d1ecf1';
            
            return `
                <div class="associacao-item" style="background: ${cor};">
                    <div class="associacao-detalhes">
                        <strong>${assoc.nome}</strong>
                        <small>${detalhes}</small>
                    </div>
                    <button class="btn-remover-associacao" data-index="${index}">
                        🗑️ Remover
                    </button>
                </div>
            `;
        }).join('');
        
        // Eventos de remover
        lista.querySelectorAll('.btn-remover-associacao').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                const assoc = this.associacoesTemporarias[index];
                
                const card = document.querySelector(`.eletricista-card[data-id="${assoc.eletricista_id}"]`);
                if (card) card.style.display = 'block';
                
                this.associacoesTemporarias.splice(index, 1);
                this.atualizarListaAssociacoes();
            });
        });
    }
    
    // ✅ FUNÇÃO CORRIGIDA: MOSTRAR REGISTROS SALVOS (ACUMULAR)
    mostrarRegistrosSalvos(associacoes, dataSalva) {
        const container = document.getElementById('registros-salvos');
        const lista = document.getElementById('lista-salvos');
        
        if (!container || !lista) return;
        
        // ✅ MOSTRAR CONTAINER SE ESTIVER OCULTO
        if (container.style.display === 'none') {
            container.style.display = 'block';
        }
        
        // Agrupar por prefixo
        const porPrefixo = {};
        
        associacoes.forEach(assoc => {
            if (!porPrefixo[assoc.prefixo]) {
                porPrefixo[assoc.prefixo] = [];
            }
            porPrefixo[assoc.prefixo].push(assoc);
        });
        
        // ✅ GERAR HTML DO NOVO BLOCO (não apagar o anterior!)
        let novoBloco = '';
        
        // Para cada prefixo
        Object.keys(porPrefixo).sort().forEach(prefixo => {
            const eletricistas = porPrefixo[prefixo];
            
            novoBloco += `
                <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #667eea;">
                    <div style="font-weight: bold; color: #667eea; margin-bottom: 10px; font-size: 16px;">
                        🚗 Prefixo: ${prefixo}
                    </div>
                    <div style="padding-left: 15px;">
            `;
            
            eletricistas.forEach((elet, index) => {
                novoBloco += `
                    <div style="padding: 8px 0; border-bottom: 1px solid #f0f0f0;">
                        <strong>${index + 1}. ${elet.nome}</strong><br>
                        <small style="color: #666;">Matrícula: ${elet.matricula}</small>
                    </div>
                `;
            });
            
            novoBloco += `
                    </div>
                </div>
            `;
        });
        
        // ✅ SE FOR O PRIMEIRO REGISTRO, ADICIONAR CABEÇALHO
        if (lista.innerHTML.trim() === '') {
            lista.innerHTML = `
                <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #28a745;">
                    <strong>📅 Data:</strong> ${dataSalva}<br>
                    <strong>📊 Registros realizados nesta sessão</strong>
                </div>
            `;
        }
        
        // ✅ ADICIONAR O NOVO BLOCO AO FINAL (não substituir!)
        lista.innerHTML += novoBloco;
        
        // Scroll suave até a seção
        setTimeout(() => {
            container.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }
    
    // ==========================================
    // SEÇÃO 2: REMANEJADO
    // ==========================================
    setupRemanejado() {
        const inputBusca = document.getElementById('busca-remanejar');
        const resultadoDiv = document.getElementById('resultado-busca-remanejar');
        let debounceTimer = null;
        
        if (!inputBusca) return;
        
        inputBusca.addEventListener('input', (e) => {
            const termo = e.target.value.trim();
            
            clearTimeout(debounceTimer);
            
            if (termo.length < 3) {
                resultadoDiv.innerHTML = '';
                return;
            }
            
            debounceTimer = setTimeout(async () => {
                try {
                    // Pegar data selecionada
                    const dataRegistro = document.getElementById('data-registro').value;
                    
                    const apiUrl = `/api/buscar-eletricistas-remanejar?q=${encodeURIComponent(termo)}&data=${dataRegistro}`;
                    
                    const response = await fetch(apiUrl);
                    const data = await response.json();
                    
                    if (data.eletricistas.length === 0) {
                        resultadoDiv.innerHTML = '<p style="color: #999;">Nenhum eletricista encontrado</p>';
                    } else {
                        resultadoDiv.innerHTML = data.eletricistas.map(elet => `
                            <div class="resultado-item" style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 2px solid #e0e0e0;">
                                <div style="margin-bottom: 10px;">
                                    <strong>${elet.nome}</strong><br>
                                    <small>Mat: ${elet.matricula} | Base: ${elet.base} | Supervisor: ${elet.polo || 'N/A'}</small>
                                </div>
                                <button class="btn btn-primary" onclick="remanejarEletricista(${elet.id}, '${elet.nome}', '${elet.base}')">
                                    🔄 Remanejar para Minha Supervisão
                                </button>
                            </div>
                        `).join('');
                    }
                    
                } catch (error) {
                    console.error('❌ [REMANEJAR] Erro:', error);
                    resultadoDiv.innerHTML = '<p style="color: red;">❌ Erro ao buscar eletricistas</p>';
                }
            }, 300);
        });
    }
    
    // ==========================================
    // SEÇÃO 3: INDISPONÍVEL
    // ==========================================
    setupIndisponivel() {
        const form = document.getElementById('form-indisponivel');
        const inputEletricista = document.getElementById('eletricista-indisponivel');
        const inputEletricstaId = document.getElementById('eletricista-id-indisponivel');
        
        if (!form || !inputEletricista) return;
        
        // Autocomplete para eletricista
        new AutocompleteIndisponivel(inputEletricista, inputEletricstaId);
        
        // Submit do formulário
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const eletricstaId = inputEletricstaId.value;
            
            if (!eletricstaId) {
                alert('⚠️ Selecione um eletricista da lista!');
                return;
            }
            
            if (!confirm('⚠️ Confirmar registro de indisponibilidade?')) {
                return;
            }
            
            try {
                const submitBtn = form.querySelector('button[type="submit"]');
                submitBtn.disabled = true;
                submitBtn.textContent = '⏳ Salvando...';                
                
                // Adicionar data ao FormData
                const dataRegistro = document.getElementById('data-registro').value;
                formData.append('data', dataRegistro);
                
                const response = await fetch('/api/salvar-indisponibilidade', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('✅ Indisponibilidade registrada com sucesso!');
                    window.location.reload();
                } else {
                    alert(`❌ Erro: ${result.erro}`);
                }
                
            } catch (error) {
                alert('❌ Erro ao salvar: ' + error.message);
            }
        });
    }
}

// ==========================================
// AUTOCOMPLETE PARA INDISPONÍVEL
// ==========================================
class AutocompleteIndisponivel {
    constructor(inputElement, hiddenIdElement) {
        this.input = inputElement;
        this.hiddenId = hiddenIdElement;
        this.sugestoes = null;
        this.debounceTimer = null;
        
        this.init();
    }
    
    init() {
        this.criarElementoSugestoes();
        
        this.input.addEventListener('input', (e) => this.handleInput(e));
        
        document.addEventListener('click', (e) => {
            if (!this.input.contains(e.target) && !this.sugestoes.contains(e.target)) {
                this.fecharSugestoes();
            }
        });
    }
    
    criarElementoSugestoes() {
        this.sugestoes = document.createElement('div');
        this.sugestoes.className = 'autocomplete-sugestoes';
        this.sugestoes.style.display = 'none';
        
        this.input.parentNode.style.position = 'relative';
        this.input.parentNode.appendChild(this.sugestoes);
    }
    
    handleInput(e) {
        const valor = e.target.value.trim();
        
        clearTimeout(this.debounceTimer);
        this.hiddenId.value = '';
        
        if (valor.length < 3) {
            this.fecharSugestoes();
            return;
        }
        
        this.debounceTimer = setTimeout(() => {
            this.buscarEletricistas(valor);
        }, 300);
    }
    
    async buscarEletricistas(termo) {
        try {
            
            // Pegar data selecionada
            const dataRegistro = document.getElementById('data-registro').value;        
            const response = await fetch(`/api/buscar-eletricistas?q=${encodeURIComponent(termo)}&data=${dataRegistro}`);
            
            const data = await response.json();
            
            this.mostrarSugestoes(data.eletricistas);
            
        } catch (error) {
            console.error('Erro ao buscar:', error);
        }
    }
    
    mostrarSugestoes(eletricistas) {
        this.sugestoes.innerHTML = '';
        
        if (eletricistas.length === 0) {
            this.sugestoes.innerHTML = '<div class="autocomplete-item autocomplete-vazio">Nenhum eletricista encontrado</div>';
            this.sugestoes.style.display = 'block';
            return;
        }
        
        eletricistas.forEach(elet => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.innerHTML = `
                <div class="autocomplete-nome">${elet.nome}</div>
                <div class="autocomplete-detalhes">
                    Mat: ${elet.matricula} | Base: ${elet.base}
                </div>
            `;
            
            item.addEventListener('click', () => {
                this.selecionarEletricista(elet);
            });
            
            this.sugestoes.appendChild(item);
        });
        
        this.sugestoes.style.display = 'block';
    }
    
    selecionarEletricista(elet) {
        this.input.value = elet.nome;
        this.hiddenId.value = elet.id;
        
        // Sugerir prefixo
        const prefixoInput = document.getElementById('prefixo-indisponivel');
        if (prefixoInput && !prefixoInput.value) {
            prefixoInput.value = elet.prefixo;
        }
        
        this.fecharSugestoes();
    }
    
    fecharSugestoes() {
        this.sugestoes.style.display = 'none';
    }
}

// ==========================================
// FUNÇÃO GLOBAL PARA REMANEJAMENTO
// ==========================================
async function remanejarEletricista(id, nome, base) {
    if (!confirm(`🔄 Remanejar ${nome} (Base: ${base}) para sua supervisão?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/remanejar-eletricista', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ eletricista_id: id })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`✅ ${nome} foi remanejado com sucesso!\n\nAgora você pode associá-lo na seção FREQUÊNCIA.`);
            // Recarregar para atualizar lista
            window.location.reload();
        } else {
            alert(`❌ Erro: ${result.erro}`);
        }
        
    } catch (error) {
        alert('❌ Erro ao remanejar: ' + error.message);
    }
}

// =============================================
// CALENDÁRIO - FILTRO DE DATA
// =============================================
function inicializarCalendario() {
    const dataInput = document.getElementById('data-registro');
    if (dataInput) {
        dataInput.addEventListener('change', function() {
            const dataSelecionada = this.value;
            // Recarregar página com nova data
            window.location.href = `/registrar-v2?data=${dataSelecionada}`;
        });
    }
}

// =============================================
// INICIALIZAR QUANDO PÁGINA CARREGAR
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    new RegistroV2();
    inicializarCalendario(); // Inicializar filtro de data
});

