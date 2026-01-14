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
    // SEÇÃO 1: FREQUÊNCIA
    // ==========================================
    setupFrequencia() {
        const checkboxes = document.querySelectorAll('.eletricista-checkbox');
        const eletricistagInfo = document.getElementById('eletricista-info');
        const prefixoInput = document.getElementById('prefixo-frequencia');
        const btnAssociar = document.getElementById('btn-associar');
        const btnSalvarFrequencia = document.getElementById('btn-salvar-frequencia');
        const btnLimparTodas = document.getElementById('btn-limpar-todas');
        
        let eletricistaSelecionado = null;
        
        // Permitir apenas 1 checkbox marcado por vez
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    // Desmarcar todos os outros
                    checkboxes.forEach(cb => {
                        if (cb !== e.target) cb.checked = false;
                    });
                    
                    // Guardar eletricista selecionado
                    eletricistaSelecionado = {
                        id: e.target.closest('.eletricista-card').dataset.id,
                        nome: e.target.dataset.nome,
                        matricula: e.target.dataset.matricula,
                        prefixo: e.target.dataset.prefixo,
                        base: e.target.dataset.base
                    };
                    
                    // Atualizar painel de informações
                    eletricistagInfo.innerHTML = `
                        <strong>${eletricistaSelecionado.nome}</strong><br>
                        <small>Mat: ${eletricistaSelecionado.matricula} | Base: ${eletricistaSelecionado.base}</small>
                    `;
                    eletricistagInfo.classList.add('info-preenchida');
                    eletricistagInfo.classList.remove('info-vazia');
                    
                    // Sugerir prefixo
                    prefixoInput.value = eletricistaSelecionado.prefixo;
                    
                    // Habilitar botão associar
                    btnAssociar.disabled = false;
                    
                } else {
                    // Se desmarcou, limpar
                    eletricistaSelecionado = null;
                    eletricistagInfo.innerHTML = 'Selecione um eletricista acima';
                    eletricistagInfo.classList.remove('info-preenchida');
                    eletricistagInfo.classList.add('info-vazia');
                    prefixoInput.value = '';
                    btnAssociar.disabled = true;
                }
            });
        });
        
        // Botão Associar
        btnAssociar.addEventListener('click', () => {
            if (!eletricistaSelecionado) return;
            
            const prefixo = prefixoInput.value.trim();
            
            if (!prefixo) {
                alert('⚠️ Informe o prefixo da equipe!');
                prefixoInput.focus();
                return;
            }
            
            // Verificar se já foi associado
            const jaAssociado = this.associacoesTemporarias.find(
                a => a.eletricista_id === eletricistaSelecionado.id
            );
            
            if (jaAssociado) {
                alert('⚠️ Este eletricista já foi associado!');
                return;
            }
            
            // Adicionar à lista temporária
            this.associacoesTemporarias.push({
                eletricista_id: eletricistaSelecionado.id,
                nome: eletricistaSelecionado.nome,
                matricula: eletricistaSelecionado.matricula,
                prefixo: prefixo
            });
            
            // Remover card da lista (eletricista "acabou")
            const card = document.querySelector(`.eletricista-card[data-id="${eletricistaSelecionado.id}"]`);
            card.style.display = 'none';
            
            // Limpar seleção
            checkboxes.forEach(cb => cb.checked = false);
            eletricistagInfo.innerHTML = 'Selecione um eletricista acima';
            eletricistagInfo.classList.remove('info-preenchida');
            eletricistagInfo.classList.add('info-vazia');
            prefixoInput.value = '';
            btnAssociar.disabled = true;
            eletricistaSelecionado = null;
            
            // Atualizar lista de associações
            this.atualizarListaAssociacoes();
        });
        
        // Botão Salvar Frequência
        if (btnSalvarFrequencia) {
            btnSalvarFrequencia.addEventListener('click', async () => {
                if (this.associacoesTemporarias.length === 0) {
                    alert('⚠️ Não há associações para salvar!');
                    return;
                }
                
                if (!confirm(`💾 Salvar ${this.associacoesTemporarias.length} associação(ões)?`)) {
                    return;
                }
                
                try {
                    btnSalvarFrequencia.disabled = true;
                    btnSalvarFrequencia.textContent = '⏳ Salvando...';
                    
                    const response = await fetch('/api/salvar-frequencia', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ associacoes: this.associacoesTemporarias })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        alert(`✅ ${result.total} associação(ões) salva(s) com sucesso!`);
                        window.location.reload();
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
                
                // Mostrar todos os cards novamente
                document.querySelectorAll('.eletricista-card').forEach(card => {
                    card.style.display = 'block';
                });
                
                // Limpar lista
                this.associacoesTemporarias = [];
                this.atualizarListaAssociacoes();
            });
        }
    }
    
    atualizarListaAssociacoes() {
        const container = document.getElementById('associacoes-temporarias');
        const lista = document.getElementById('lista-associacoes');
        
        if (this.associacoesTemporarias.length === 0) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'block';
        
        lista.innerHTML = this.associacoesTemporarias.map((assoc, index) => `
            <div class="associacao-item">
                <div class="associacao-detalhes">
                    <strong>${assoc.nome}</strong>
                    <small>Mat: ${assoc.matricula} → Prefixo: ${assoc.prefixo}</small>
                </div>
                <button class="btn-remover-associacao" data-index="${index}">
                    🗑️ Remover
                </button>
            </div>
        `).join('');
        
        // Adicionar eventos aos botões de remover
        lista.querySelectorAll('.btn-remover-associacao').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                const assoc = this.associacoesTemporarias[index];
                
                // Mostrar card novamente
                const card = document.querySelector(`.eletricista-card[data-id="${assoc.eletricista_id}"]`);
                if (card) card.style.display = 'block';
                
                // Remover da lista
                this.associacoesTemporarias.splice(index, 1);
                this.atualizarListaAssociacoes();
            });
        });
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
                    const response = await fetch(`/api/buscar-eletricistas?q=${encodeURIComponent(termo)}`);
                    const data = await response.json();
                    
                    this.mostrarResultadosRemanejamento(data.eletricistas, resultadoDiv);
                    
                } catch (error) {
                    console.error('Erro ao buscar:', error);
                }
            }, 300);
        });
    }
    
    mostrarResultadosRemanejamento(eletricistas, container) {
        if (eletricistas.length === 0) {
            container.innerHTML = '<p style="color: #999;">Nenhum eletricista encontrado</p>';
            return;
        }
        
        container.innerHTML = eletricistas.map(elet => `
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
            const response = await fetch(`/api/buscar-eletricistas?q=${encodeURIComponent(termo)}`);
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

// ==========================================
// INICIALIZAR QUANDO PÁGINA CARREGAR
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    new RegistroV2();
});