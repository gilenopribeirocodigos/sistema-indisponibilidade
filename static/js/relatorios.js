// ==========================================
// RELATÓRIOS - JAVASCRIPT
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    
    // Elementos
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const tipoPeriodo = document.getElementById('tipo-periodo');
    const filtroDia = document.getElementById('filtro-dia');
    const filtroPeriodo = document.getElementById('filtro-periodo');
    const btnGerar = document.getElementById('btn-gerar-relatorio');
    
    let tabAtual = 'geral';
    
    // ==========================================
    // GERENCIAR ABAS
    // ==========================================
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            // Atualizar botões
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Atualizar conteúdo
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`tab-${tab}`).classList.add('active');
            
            tabAtual = tab;
        });
    });
    
    // ==========================================
    // CONTROLAR TIPO DE PERÍODO
    // ==========================================
    
    tipoPeriodo.addEventListener('change', () => {
        if (tipoPeriodo.value === 'dia') {
            filtroDia.style.display = 'flex';
            filtroPeriodo.style.display = 'none';
        } else {
            filtroDia.style.display = 'none';
            filtroPeriodo.style.display = 'flex';
        }
    });
    
    // ==========================================
    // GERAR RELATÓRIO
    // ==========================================
    
    btnGerar.addEventListener('click', () => {
        if (tabAtual === 'geral') {
            gerarRelatorioGeral();
        } else {
            gerarRelatorioPorSupervisor();
        }
    });
    
    // ==========================================
    // RELATÓRIO GERAL
    // ==========================================
    
    async function gerarRelatorioGeral() {
        try {
            // Obter datas
            let dataInicio, dataFim;
            
            if (tipoPeriodo.value === 'dia') {
                dataInicio = document.getElementById('data-dia').value;
                dataFim = dataInicio;
            } else {
                dataInicio = document.getElementById('data-inicio').value;
                dataFim = document.getElementById('data-fim').value;
            }
            
            if (!dataInicio || !dataFim) {
                alert('⚠️ Selecione o período');
                return;
            }
            
            // Fazer requisição
            const response = await fetch(
                `/api/relatorio-geral?data_inicio=${dataInicio}&data_fim=${dataFim}`
            );
            
            const data = await response.json();
            
            if (!data.success) {
                alert(`❌ Erro: ${data.erro}`);
                return;
            }
            
            // Atualizar informações
            document.getElementById('relatorio-geral-info').style.display = 'block';
            document.getElementById('geral-periodo').textContent = 
                `${data.periodo.inicio} até ${data.periodo.fim} (${data.periodo.dias} dia(s))`;
            document.getElementById('geral-total-eletricistas').textContent = data.total_eletricistas;
            document.getElementById('geral-total-registros').textContent = data.total_registros;
            
            // Renderizar tabela
            const tbody = document.querySelector('#tabela-geral tbody');
            tbody.innerHTML = '';
            
            data.dados.forEach(item => {
                const tr = document.createElement('tr');
                
                const tdMotivo = document.createElement('td');
                tdMotivo.textContent = item.motivo;
                
                const tdQtde = document.createElement('td');
                tdQtde.textContent = item.qtde;
                
                const tdPerc = document.createElement('td');
                tdPerc.textContent = `${item.percentual}%`;
                
                // Cor no percentual
                if (item.motivo === 'Presente') {
                    tdPerc.classList.add('percentual-alta');
                } else if (item.motivo === 'Não registrado') {
                    tdPerc.classList.add('percentual-media');
                }
                
                tr.appendChild(tdMotivo);
                tr.appendChild(tdQtde);
                tr.appendChild(tdPerc);
                tbody.appendChild(tr);
            });
            
            // Atualizar total
            document.getElementById('geral-total-qtde').textContent = data.total_registros;
            
            // Mostrar tabela
            document.getElementById('container-tabela-geral').style.display = 'block';
            
            // Atualizar data de geração
            const agora = new Date();
            document.getElementById('data-geracao').textContent = 
                agora.toLocaleString('pt-BR');
            
        } catch (error) {
            alert(`❌ Erro ao gerar relatório: ${error.message}`);
            console.error(error);
        }
    }
    
    // ==========================================
    // RELATÓRIO POR SUPERVISOR
    // ==========================================
    
    async function gerarRelatorioPorSupervisor() {
        try {
            // Obter datas
            let dataInicio, dataFim;
            
            if (tipoPeriodo.value === 'dia') {
                dataInicio = document.getElementById('data-dia').value;
                dataFim = dataInicio;
            } else {
                dataInicio = document.getElementById('data-inicio').value;
                dataFim = document.getElementById('data-fim').value;
            }
            
            if (!dataInicio || !dataFim) {
                alert('⚠️ Selecione o período');
                return;
            }
            
            // Fazer requisição
            const response = await fetch(
                `/api/relatorio-por-supervisor?data_inicio=${dataInicio}&data_fim=${dataFim}`
            );
            
            const data = await response.json();
            
            if (!data.success) {
                alert(`❌ Erro: ${data.erro}`);
                return;
            }
            
            // Verificar se há dados
            if (!data.dados || data.dados.length === 0) {
                alert('⚠️ Nenhum dado encontrado no período selecionado');
                return;
            }
            
            // Atualizar informações
            document.getElementById('relatorio-sup-info').style.display = 'block';
            document.getElementById('sup-periodo').textContent = 
                `${data.periodo.inicio} até ${data.periodo.fim} (${data.periodo.dias} dia(s))`;
            document.getElementById('sup-total-registros').textContent = data.total_geral || 0;
            
            // Lista de motivos na ordem da tabela
            const motivos = [
                'Atestado Médico',
                'Falta Injustificada',
                'Viatura com Defeito',
                'Viatura em Manutenção',
                'Acidente',
                'Treinamento',
                'Férias',
                'Licença',
                'Outro'
            ];
            
            // DEBUG: Ver o que vem nos dados
            console.log('Dados recebidos:', data.dados);
            if (data.dados.length > 0) {
                console.log('Contadores do primeiro supervisor:', data.dados[0].contadores);
                console.log('Todas as chaves nos contadores:', Object.keys(data.dados[0].contadores));
            }
            
            // Função para encontrar motivo nos contadores (case insensitive)
            function buscarMotivo(contadores, motivoProcurado) {
                // Tentar exato primeiro
                if (contadores[motivoProcurado] !== undefined) {
                    return contadores[motivoProcurado];
                }
                
                // Tentar case-insensitive
                const motivoLower = motivoProcurado.toLowerCase();
                for (let chave in contadores) {
                    if (chave.toLowerCase() === motivoLower) {
                        return contadores[chave];
                    }
                }
                
                return 0;
            }
            
            // ========================================
            // RENDERIZAR DADOS
            // ========================================
            const tbody = document.querySelector('#tabela-supervisor tbody');
            tbody.innerHTML = '';
            
            // Calcular totais gerais
            let totalPresentes = 0;
            let totalRegistros = 0;
            const totaisMotivos = {};
            motivos.forEach(m => totaisMotivos[m] = 0);
            
            data.dados.forEach(sup => {
                const tr = document.createElement('tr');
                
                const contadores = sup.contadores || {};
                
                // Supervisor
                const tdSup = document.createElement('td');
                tdSup.innerHTML = `<strong>${sup.supervisor || 'N/A'}</strong>`;
                tr.appendChild(tdSup);
                
                // Presentes
                const tdPresentes = document.createElement('td');
                const qtdPresentes = contadores.Presente || 0;
                tdPresentes.textContent = qtdPresentes;
                tr.appendChild(tdPresentes);
                totalPresentes += qtdPresentes;
                
                // Contadores de motivos
                motivos.forEach(motivo => {
                    const td = document.createElement('td');
                    const qtd = buscarMotivo(contadores, motivo);
                    td.textContent = qtd;
                    tr.appendChild(td);
                    totaisMotivos[motivo] += qtd;
                });
                
                // Total registros
                const tdTotalReg = document.createElement('td');
                const totalReg = sup.total_registros || 0;
                tdTotalReg.innerHTML = `<strong>${totalReg}</strong>`;
                tr.appendChild(tdTotalReg);
                totalRegistros += totalReg;
                
                // === COLUNAS DE PERCENTUAL ===
                
                // % Presentes
                const percPresentes = totalReg > 0 ? ((qtdPresentes / totalReg) * 100).toFixed(1) : 0;
                const tdPercPresentes = document.createElement('td');
                tdPercPresentes.textContent = `${percPresentes}%`;
                tdPercPresentes.classList.add('col-percentual');
                tr.appendChild(tdPercPresentes);
                
                // % dos motivos
                motivos.forEach(motivo => {
                    const qtd = buscarMotivo(contadores, motivo);
                    const perc = totalReg > 0 ? ((qtd / totalReg) * 100).toFixed(1) : 0;
                    const td = document.createElement('td');
                    td.textContent = `${perc}%`;
                    td.classList.add('col-percentual');
                    tr.appendChild(td);
                });
                
                tbody.appendChild(tr);
            });
            
            // Adicionar linha de TOTAL
            const trTotal = document.createElement('tr');
            trTotal.classList.add('linha-total');
            
            // Supervisor = TOTAL
            const tdTotalLabel = document.createElement('td');
            tdTotalLabel.innerHTML = '<strong>TOTAL</strong>';
            trTotal.appendChild(tdTotalLabel);
            
            // Total Presentes
            const tdTotalPresentes = document.createElement('td');
            tdTotalPresentes.innerHTML = `<strong>${totalPresentes}</strong>`;
            trTotal.appendChild(tdTotalPresentes);
            
            // Totais dos motivos
            motivos.forEach(motivo => {
                const td = document.createElement('td');
                td.innerHTML = `<strong>${totaisMotivos[motivo]}</strong>`;
                trTotal.appendChild(td);
            });
            
            // Total de registros
            const tdTotalGeral = document.createElement('td');
            tdTotalGeral.innerHTML = `<strong>${totalRegistros}</strong>`;
            trTotal.appendChild(tdTotalGeral);
            
            // === PERCENTUAIS TOTAIS ===
            
            // % Presentes total
            const percPresentesTotal = totalRegistros > 0 ? ((totalPresentes / totalRegistros) * 100).toFixed(1) : 0;
            const tdPercPresentesTotal = document.createElement('td');
            tdPercPresentesTotal.innerHTML = `<strong>${percPresentesTotal}%</strong>`;
            tdPercPresentesTotal.classList.add('col-percentual');
            trTotal.appendChild(tdPercPresentesTotal);
            
            // % dos motivos totais
            motivos.forEach(motivo => {
                const perc = totalRegistros > 0 ? ((totaisMotivos[motivo] / totalRegistros) * 100).toFixed(1) : 0;
                const td = document.createElement('td');
                td.innerHTML = `<strong>${perc}%</strong>`;
                td.classList.add('col-percentual');
                trTotal.appendChild(td);
            });
            
            tbody.appendChild(trTotal);
            
            // Mostrar tabela
            document.getElementById('container-tabela-sup').style.display = 'block';
            
            // Atualizar data de geração
            const agora = new Date();
            document.getElementById('data-geracao').textContent = 
                agora.toLocaleString('pt-BR');
            
        } catch (error) {
            alert(`❌ Erro ao gerar relatório: ${error.message}`);
            console.error('Erro completo:', error);
        }
    }
});
