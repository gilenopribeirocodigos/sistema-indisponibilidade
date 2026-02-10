// ==========================================
// REGISTRO V2 - INTERFACE DINÂMICA
// ==========================================

class RegistroV2 {
    constructor() {
        this.associacoesTemporarias = [];
        this.motivosDisponiveis = [];
        this.motivosCarregados = false;
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
        const checkboxes = document.querySelectorAll('.checkbox-eletricista');
        const contadorSelecao = document.getElementById('contador-selecao');
        
        const btnSalvarFrequencia = document.getElementById('btn-salvar-frequencia');
        const btnLimparTodas = document.getElementById('btn-limpar-todas');
        
        let eletricistasIntermediarios = [];
        let modoAtual = 'presenca';
        
        // ✅ CARREGAR MOTIVOS DE AUSÊNCIA (VERSÃO MELHORADA)
        const carregarMotivos = async () => {
            try {
                console.log('🔄 Iniciando carregamento de motivos...');
                
                const response = await fetch('/api/motivos-indisponibilidade');
                
                console.log('📡 Response status:', response.status);
                console.log('📡 Response ok:', response.ok);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                console.log('📦 Data recebida:', data);
                
                if (data.success) {
                    this.motivosDisponiveis = data.motivos;
                    this.motivosCarregados = true;
                    console.log(`✅ ${this.motivosDisponiveis.length} motivos carregados:`, this.motivosDisponiveis);
                    
                    if (this.motivosDisponiveis.length === 0) {
                        console.warn('⚠️ Lista de motivos está vazia!');
                    }
                } else {
                    console.error('❌ API retornou success: false');
                    console.error('❌ Erro da API:', data.erro);
                    alert(`❌ Erro do servidor: ${data.erro || 'Erro desconhecido'}`);
                }
            } catch (error) {
                console.error('❌ ERRO FATAL ao carregar motivos:');
                console.error('   Tipo:', error.name);
                console.error('   Mensagem:', error.message);
                console.error('   Stack:', error.stack);
                alert(`❌ Erro ao carregar motivos: ${error.message}\n\nVerifique o console (F12) para mais detalhes.`);
            }
        };
        
        // Carregar motivos ao iniciar
        carregarMotivos();
        
        // ✅ DETECTAR MUDANÇA NO TIPO DE REGISTRO
        document.querySelectorAll('input[name="tipo_registro"]').forEach(radio => {
            radio.addEventListener('change', () => {
                modoAtual = radio.value;
                this.limparTudo();
            });
        });
        
        // ✅ QUANDO CHECKBOX É CLICADO
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                if (modoAtual === 'presenca') {
                    this.handlePresencaClick(e.target, eletricistasIntermediarios);
                } else {
                    this.handleAusenciaClick(e.target);
                }
            });
        });
        
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
                    
                    const dataRegistro = document.querySelector('input[name="data"]').value;
                    const associacoesSalvas = [...this.associacoesTemporarias];
                    
                    const response = await fetch('/api/salvar-frequencia', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            associacoes: this.associacoesTemporarias.map(a => ({
                                eletricista_id: a.eletricista_id,
                                prefixo: a.prefixo,
                                id_indisponibilidade: a.id_indisponibilidade
                            })),
                            data: dataRegistro 
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        this.mostrarRegistrosSalvos(associacoesSalvas, result.data);
                        
                        // Remover eletricistas salvos da tela
                        this.associacoesTemporarias.forEach(assoc => {
                            const card = document.querySelector(`.eletricista-card[data-id="${assoc.eletricista_id}"]`);
                            if (card) card.remove();
                        });
                        
                        this.associacoesTemporarias = [];
                        this.atualizarListaAssociacoes();
                        
                        document.getElementById('painelAssociacoes').style.display = 'none';
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
                
                this.limparTudo();
            });
        }
    }
    
    // ==========================================
    // PRESENÇA: CLICK NO CHECKBOX
    // ==========================================
    handlePresencaClick(checkbox, eletricistasIntermediarios) {
        const eletId = checkbox.value;
        const eletNome = checkbox.dataset.nome;
        const prefixoSugerido = checkbox.dataset.prefixo;
        
        if (checkbox.checked) {
            // Verificar limite
            const limite = 2;
            const atual = document.querySelectorAll('.checkbox-eletricista:checked').length;
            
            if (atual > limite) {
                alert('⚠️ Você já selecionou 2 eletricistas! Remova um antes de adicionar outro.');
                checkbox.checked = false;
                return;
            }
            
            // Adicionar à lista temporária
            eletricistasIntermediarios.push({
                eletricista_id: eletId,
                nome: eletNome,
                prefixo: prefixoSugerido
            });
            
        } else {
            // Remover da lista
            const index = eletricistasIntermediarios.findIndex(e => e.eletricista_id === eletId);
            if (index > -1) {
                eletricistasIntermediarios.splice(index, 1);
            }
        }
        
        // Atualizar painel intermediário
        this.atualizarPainelIntermediario(eletricistasIntermediarios);
    }
    
    // ==========================================
    // AUSÊNCIA: CLICK NO CHECKBOX
    // ==========================================
    async handleAusenciaClick(checkbox) {
        const eletId = checkbox.value;
        const eletNome = checkbox.dataset.nome;
        const prefixoSugerido = checkbox.dataset.prefixo;
        
        if (checkbox.checked) {
            // Garantir que motivos estejam carregados
            if (!this.motivosCarregados || this.motivosDisponiveis.length === 0) {
                console.log('⏳ Aguardando motivos...');
                checkbox.checked = false;
                alert('❌ Erro ao carregar motivos de ausência. Tente novamente.');
                return;
            }
            
            // Desmarcar outros
            document.querySelectorAll('.checkbox-eletricista').forEach(cb => {
                if (cb !== checkbox) {
                    cb.checked = false;
                }
            });
            
            // Abrir modal
            this.abrirModalMotivo(eletId, eletNome, prefixoSugerido, checkbox);
            
        } else {
            this.associacoesTemporarias = this.associacoesTemporarias.filter(a => a.eletricista_id !== eletId);
            this.atualizarListaAssociacoes();
        }
    }
    
    // ==========================================
    // PAINEL INTERMEDIÁRIO (PRESENÇA)
    // ==========================================
    atualizarPainelIntermediario(eletricistasIntermediarios) {
        const painel = document.getElementById('painelIntermediario');
        const lista = document.getElementById('listaIntermediaria');
        const inputPrefixo = document.getElementById('prefixoIntermediario');
        
        if (!painel) return;
        
        if (eletricistasIntermediarios.length === 0) {
            painel.style.display = 'none';
            return;
        }
        
        painel.style.display = 'block';
        
        // Montar lista
        let html = '<div style="background: white; padding: 15px; border-radius: 5px; border: 2px solid #ffc107;">';
        html += '<strong>Eletricistas Selecionados:</strong><br><br>';
        
        eletricistasIntermediarios.forEach((elet, idx) => {
            html += `
                <div style="padding: 8px; margin: 5px 0; background: #f8f9fa; border-radius: 3px;">
                    ${idx + 1}. <strong>${elet.nome}</strong><br>
                    <small>Mat: ${elet.eletricista_id} | Prefixo atual: ${elet.prefixo}</small>
                </div>
            `;
        });
        
        html += '</div>';
        lista.innerHTML = html;
        
        // Sugerir prefixo
        if (!inputPrefixo.value) {
            inputPrefixo.value = eletricistasIntermediarios[0].prefixo;
        }
        
        // Scroll
        setTimeout(() => {
            painel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
        
        // Adicionar evento ao botão confirmar (se não existir)
        const btnConfirmar = document.querySelector('#painelIntermediario button[onclick*="confirmarAssociacao"]');
        if (btnConfirmar && !btnConfirmar.dataset.listenerAdded) {
            btnConfirmar.dataset.listenerAdded = 'true';
            btnConfirmar.onclick = () => this.confirmarAssociacao(eletricistasIntermediarios);
        }
        
        const btnLimpar = document.querySelector('#painelIntermediario button[onclick*="limparSelecaoIntermediaria"]');
        if (btnLimpar && !btnLimpar.dataset.listenerAdded) {
            btnLimpar.dataset.listenerAdded = 'true';
            btnLimpar.onclick = () => this.limparSelecaoIntermediaria(eletricistasIntermediarios);
        }
    }
    
    // ==========================================
    // CONFIRMAR ASSOCIAÇÃO (PRESENÇA)
    // ==========================================
    confirmarAssociacao(eletricistasIntermediarios) {
        const prefixo = document.getElementById('prefixoIntermediario').value.trim();
        
        if (!prefixo) {
            alert('⚠️ Digite o prefixo!');
            return;
        }
        
        // Mover para pendentes
        eletricistasIntermediarios.forEach(elet => {
            this.associacoesTemporarias.push({
                eletricista_id: elet.eletricista_id,
                nome: elet.nome,
                prefixo: prefixo,
                tipo: 'presenca',
                id_indisponibilidade: null
            });
        });
        
        // Limpar intermediário
        eletricistasIntermediarios.length = 0;
        document.getElementById('prefixoIntermediario').value = '';
        document.getElementById('painelIntermediario').style.display = 'none';
        
        // Atualizar painel de pendentes
        this.atualizarListaAssociacoes();
    }
    
    // ==========================================
    // LIMPAR SELEÇÃO INTERMEDIÁRIA
    // ==========================================
    limparSelecaoIntermediaria(eletricistasIntermediarios) {
        if (!confirm('Desmarcar os eletricistas selecionados?')) {
            return;
        }
        
        // Desmarcar checkboxes
        eletricistasIntermediarios.forEach(elet => {
            const checkbox = document.querySelector(`.checkbox-eletricista[value="${elet.eletricista_id}"]`);
            if (checkbox) {
                checkbox.checked = false;
            }
        });
        
        eletricistasIntermediarios.length = 0;
        document.getElementById('prefixoIntermediario').value = '';
        document.getElementById('painelIntermediario').style.display = 'none';
    }
    

    // ==========================================
    // ABRIR MODAL AUSÊNCIA (VERSÃO 100% CORRIGIDA)
    // ==========================================
    abrirModalMotivo(eletId, eletNome, prefixo, checkbox) {
        console.log('🔵 abrirModalMotivo chamada para:', eletNome);
        
        // Remover modal antigo se existir
        const modalAntigo = document.getElementById('modalMotivo');
        if (modalAntigo) {
            modalAntigo.remove();
        }
        
        // Criar container do modal
        const modalContainer = document.createElement('div');
        modalContainer.id = 'modalMotivo';
        modalContainer.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; display: flex; align-items: center; justify-content: center;';
        
        // Criar conteúdo do modal
        const modalContent = document.createElement('div');
        modalContent.style.cssText = 'background: white; padding: 30px; border-radius: 10px; max-width: 500px; width: 90%; max-height: 90vh; overflow-y: auto;';
        
        // Título
        const titulo = document.createElement('h3');
        titulo.style.marginTop = '0';
        titulo.innerHTML = '⚠️ Selecione o Motivo da Ausência';
        modalContent.appendChild(titulo);
        
        // Nome do eletricista
        const nomeP = document.createElement('p');
        nomeP.innerHTML = `<strong>Eletricista:</strong> ${eletNome}`;
        modalContent.appendChild(nomeP);
        
        // Label
        const label = document.createElement('label');
        label.style.cssText = 'display: block; margin-top: 20px; font-weight: bold;';
        label.textContent = 'Motivo:';
        modalContent.appendChild(label);
        
        // Select
        const select = document.createElement('select');
        select.id = 'selectMotivo';
        select.style.cssText = 'width: 100%; padding: 10px; margin-top: 10px; font-size: 16px; box-sizing: border-box;';
        
        // Adicionar opção vazia
        const optionVazia = document.createElement('option');
        optionVazia.value = '';
        optionVazia.textContent = '-- Selecione --';
        select.appendChild(optionVazia);
        
        // Adicionar motivos
        console.log('🔵 Adicionando motivos ao select:', this.motivosDisponiveis);
        this.motivosDisponiveis.forEach(motivo => {
            const option = document.createElement('option');
            option.value = motivo.id;
            option.textContent = motivo.descricao;
            select.appendChild(option);
        });
        
        modalContent.appendChild(select);
        
        // Container dos botões
        const botoesDiv = document.createElement('div');
        botoesDiv.style.cssText = 'margin-top: 30px; display: flex; gap: 10px;';
        
        // ✅ Botão Confirmar (COM addEventListener)
        const btnConfirmar = document.createElement('button');
        btnConfirmar.id = 'btnConfirmarMotivo';
        btnConfirmar.type = 'button'; // Importante!
        btnConfirmar.innerHTML = '✅ Confirmar';
        btnConfirmar.style.cssText = 'flex: 1; padding: 12px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;';
        
        btnConfirmar.addEventListener('click', () => {
            console.log('🟢 Botão Confirmar CLICADO!');
            this.confirmarMotivo(eletId, eletNome, prefixo);
        });
        
        // ✅ Botão Cancelar (COM addEventListener)
        const btnCancelar = document.createElement('button');
        btnCancelar.id = 'btnCancelarMotivo';
        btnCancelar.type = 'button'; // Importante!
        btnCancelar.innerHTML = '❌ Cancelar';
        btnCancelar.style.cssText = 'flex: 1; padding: 12px; background: #dc3545; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;';
        
        btnCancelar.addEventListener('click', () => {
            console.log('🔴 Botão Cancelar CLICADO!');
            this.fecharModalMotivo(checkbox);
        });
        
        botoesDiv.appendChild(btnConfirmar);
        botoesDiv.appendChild(btnCancelar);
        modalContent.appendChild(botoesDiv);
        
        // Montar modal
        modalContainer.appendChild(modalContent);
        document.body.appendChild(modalContainer);
        
        console.log('✅ Modal criado com sucesso!');
        console.log('✅ Botões anexados:', {
            confirmar: btnConfirmar,
            cancelar: btnCancelar
        });
    }    
    
    // ==========================================
    // CONFIRMAR MOTIVO (AUSÊNCIA)
    // ==========================================
    confirmarMotivo(eletId, eletNome, prefixo) {
        console.log('🔵 confirmarMotivo chamada!');
        console.log('   eletId:', eletId);
        console.log('   eletNome:', eletNome);
        console.log('   prefixo:', prefixo);
        
        const selectMotivo = document.getElementById('selectMotivo');
        
        if (!selectMotivo) {
            console.error('❌ Select de motivo não encontrado!');
            alert('❌ Erro: Select não encontrado');
            return;
        }
        
        const motivoId = selectMotivo.value;
        console.log('   motivoId selecionado:', motivoId);
        
        if (!motivoId) {
            alert('⚠️ Selecione um motivo!');
            return;
        }
        
        const motivo = this.motivosDisponiveis.find(m => m.id == motivoId);
        console.log('   Motivo encontrado:', motivo);
        
        if (!motivo) {
            console.error('❌ Motivo não encontrado no array!');
            alert('❌ Erro: Motivo não encontrado');
            return;
        }
        
        const motivoDescricao = motivo.descricao;
        
        // Adicionar às associações pendentes
        this.associacoesTemporarias.push({
            eletricista_id: eletId,
            nome: eletNome,
            prefixo: prefixo,
            tipo: 'ausencia',
            id_indisponibilidade: motivoId,
            motivo_descricao: motivoDescricao
        });
        
        console.log('✅ Associação adicionada:', this.associacoesTemporarias);
        
        // Fechar modal
        this.fecharModalMotivo(null);
        
        // Atualizar painel
        this.atualizarListaAssociacoes();
    }
    
    // ==========================================
    // FECHAR MODAL MOTIVO
    // ==========================================
    fecharModalMotivo(checkbox) {
        const modal = document.getElementById('modalMotivo');
        if (modal) {
            modal.remove();
        }
        
        if (checkbox) {
            checkbox.checked = false;
        }
    }

        
    // ==========================================
    // LIMPAR TUDO
    // ==========================================
    limparTudo() {
        this.associacoesTemporarias = [];
        
        document.querySelectorAll('.checkbox-eletricista').forEach(cb => {
            cb.checked = false;
        });
        
        const painelInt = document.getElementById('painelIntermediario');
        if (painelInt) painelInt.style.display = 'none';
        
        this.atualizarListaAssociacoes();
    }

    // ==========================================
    // ATUALIZAR LISTA DE ASSOCIAÇÕES PENDENTES
    // ==========================================
    atualizarListaAssociacoes() {
        const painel = document.getElementById('painelAssociacoes');
        
        if (!painel) return;
        
        if (this.associacoesTemporarias.length === 0) {
            painel.style.display = 'none';
            return;
        }
        
        painel.style.display = 'block';
        
        let html = '<div class="alert alert-warning"><h4>📋 Associações Pendentes de Salvamento:</h4>';
        
        this.associacoesTemporarias.forEach((assoc, index) => {
            if (assoc.tipo === 'presenca') {
                html += `
                    <div style="background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border: 2px solid #28a745;">
                        <strong>${assoc.nome}</strong><br>
                        Mat: ${assoc.eletricista_id} — Prefixo: <strong>${assoc.prefixo}</strong>
                        <button onclick="registroV2.removerAssociacao(${index})" style="float: right; background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">🗑️ Remover</button>
                    </div>
                `;
            } else {
                html += `
                    <div style="background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border: 2px solid #ffc107;">
                        <strong>${assoc.nome}</strong><br>
                        Mat: ${assoc.eletricista_id} — Prefixo: <strong>${assoc.prefixo}</strong><br>
                        <span style="color: #dc3545; font-weight: bold;">⚠️ Motivo: ${assoc.motivo_descricao}</span>
                        <button onclick="registroV2.removerAssociacao(${index})" style="float: right; background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">🗑️ Remover</button>
                    </div>
                `;
            }
        });
        
        // ✅ ADICIONAR BOTÕES DE AÇÃO
        html += `
            <div style="margin-top: 20px; display: flex; gap: 10px;">
                <button onclick="registroV2.limparTudo()" style="flex: 1; padding: 12px; background: #6c757d; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
                    🗑️ Limpar Todas
                </button>
                <button id="btn-salvar-frequencia-dinamico" style="flex: 2; padding: 12px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">
                    💾 Salvar Todas as Associações
                </button>
            </div>
        `;
        
        html += '</div>';
        painel.innerHTML = html;
        
        // ✅ ADICIONAR EVENTO AO BOTÃO SALVAR (DINÂMICO)
        const btnSalvar = document.getElementById('btn-salvar-frequencia-dinamico');
        if (btnSalvar) {
            btnSalvar.addEventListener('click', async () => {
                if (this.associacoesTemporarias.length === 0) {
                    alert('⚠️ Não há associações para salvar!');
                    return;
                }
                
                if (!confirm(`💾 Salvar ${this.associacoesTemporarias.length} registro(s)?`)) {
                    return;
                }
                
                try {
                    btnSalvar.disabled = true;
                    btnSalvar.textContent = '⏳ Salvando...';
                    
                    const dataRegistro = document.querySelector('input[name="data"]').value;
                    const associacoesSalvas = [...this.associacoesTemporarias];
                    
                    const response = await fetch('/api/salvar-frequencia', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            associacoes: this.associacoesTemporarias.map(a => ({
                                eletricista_id: a.eletricista_id,
                                prefixo: a.prefixo,
                                id_indisponibilidade: a.id_indisponibilidade
                            })),
                            data: dataRegistro 
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        this.mostrarRegistrosSalvos(associacoesSalvas, result.data);
                        
                        // Remover eletricistas salvos da tela
                        this.associacoesTemporarias.forEach(assoc => {
                            const card = document.querySelector(`.eletricista-card[data-id="${assoc.eletricista_id}"]`);
                            if (card) card.remove();
                        });
                        
                        this.associacoesTemporarias = [];
                        this.atualizarListaAssociacoes();
                        
                        painel.style.display = 'none';
                    } else {
                        alert(`❌ Erro: ${result.erro}`);
                    }
                    
                } catch (error) {
                    alert('❌ Erro ao salvar: ' + error.message);
                } finally {
                    btnSalvar.disabled = false;
                    btnSalvar.textContent = '💾 Salvar Todas as Associações';
                }
            });
        }
    } 
    
    removerAssociacao(index) {
        const assoc = this.associacoesTemporarias[index];
        
        const checkbox = document.querySelector(`.checkbox-eletricista[value="${assoc.eletricista_id}"]`);
        if (checkbox) {
            checkbox.checked = false;
        }
        
        this.associacoesTemporarias.splice(index, 1);
        this.atualizarListaAssociacoes();
    }
    
    // ==========================================
    // MOSTRAR REGISTROS SALVOS
    // ==========================================
    mostrarRegistrosSalvos(associacoes, dataSalva) {
        let painelSalvos = document.getElementById('painelRegistrosSalvos');
        
        if (!painelSalvos) {
            painelSalvos = document.createElement('div');
            painelSalvos.id = 'painelRegistrosSalvos';
            painelSalvos.style.marginTop = '30px';
            
            const secaoFreq = document.getElementById('secao-frequencia');
            if (secaoFreq) {
                secaoFreq.appendChild(painelSalvos);
            }
        }
        
        painelSalvos.style.display = 'block';
        
        const porPrefixo = {};
        associacoes.forEach(assoc => {
            if (!porPrefixo[assoc.prefixo]) {
                porPrefixo[assoc.prefixo] = [];
            }
            porPrefixo[assoc.prefixo].push(assoc);
        });
        
        let novoBloco = '';
        
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
                if (elet.tipo === 'presenca') {
                    novoBloco += `
                        <div style="padding: 8px 0; border-bottom: 1px solid #f0f0f0;">
                            <strong>${index + 1}. ${elet.nome}</strong><br>
                            <small style="color: #666;">Matrícula: ${elet.eletricista_id}</small>
                        </div>
                    `;
                } else {
                    novoBloco += `
                        <div style="padding: 8px 0; border-bottom: 1px solid #f0f0f0; background: #fff3cd;">
                            <strong>${index + 1}. ${elet.nome}</strong><br>
                            <small style="color: #666;">Matrícula: ${elet.eletricista_id}</small><br>
                            <span style="color: #856404;">⚠️ ${elet.motivo_descricao}</span>
                        </div>
                    `;
                }
            });
            
            novoBloco += `
                    </div>
                </div>
            `;
        });
        
        if (painelSalvos.innerHTML.trim() === '') {
            painelSalvos.innerHTML = `
                <div style="background: #d4edda; border: 2px solid #28a745; border-radius: 10px; padding: 20px;">
                    <h4 style="color: #155724; margin-top: 0;">✅ Registros Salvos com Sucesso</h4>
                    <p style="color: #155724;">📅 Data: ${dataSalva}</p>
                </div>
            `;
        }
        
        painelSalvos.innerHTML += novoBloco;
        
        setTimeout(() => {
            painelSalvos.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
                    const dataRegistro = document.querySelector('input[name="data"]').value;
                    
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
        
        new AutocompleteIndisponivel(inputEletricista, inputEletricstaId);
        
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
                
                const dataRegistro = document.querySelector('input[name="data"]').value;
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
            const dataRegistro = document.querySelector('input[name="data"]').value;        
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
    const dataInput = document.querySelector('input[name="data"]');
    if (dataInput) {
        dataInput.addEventListener('change', function() {
            const dataSelecionada = this.value;
            window.location.href = `/registrar-v2?data=${dataSelecionada}`;
        });
    }
}

// =============================================
// INICIALIZAR QUANDO PÁGINA CARREGAR
// =============================================
let registroV2;

document.addEventListener('DOMContentLoaded', () => {
    registroV2 = new RegistroV2();
    inicializarCalendario();
});




