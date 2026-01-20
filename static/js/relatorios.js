// ==========================================
// RELATÓRIOS - JAVASCRIPT
// ==========================================

document.addEventListener('DOMContentLoaded', () => {

    // =========================
    // CONTROLE DE ABAS
    // =========================
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

            btn.classList.add('active');

            const aba = btn.dataset.tab;
            const alvo = document.getElementById(`tab-${aba}`);

            if (alvo) alvo.classList.add('active');
        });
    });

    // =========================
    // BOTÃO GERAR RELATÓRIO
    // =========================
    const btnGerar = document.getElementById('btn-gerar-relatorio');
    if (btnGerar) btnGerar.addEventListener('click', gerarRelatorioPorSupervisor);

    async function gerarRelatorioPorSupervisor() {

        const tipo = document.getElementById('tipo-periodo')?.value;
        let dataInicio, dataFim;

        if (tipo === 'dia') {
            dataInicio = document.getElementById('data-dia')?.value;
            dataFim = dataInicio;
        } else {
            dataInicio = document.getElementById('data-inicio')?.value;
            dataFim = document.getElementById('data-fim')?.value;
        }

        if (!dataInicio || !dataFim) {
            alert('Selecione o período');
            return;
        }

        let response, data;

        try {
            response = await fetch(`/api/relatorio-por-supervisor?data_inicio=${dataInicio}&data_fim=${dataFim}`);
            data = await response.json();
        } catch (e) {
            alert("Erro ao conectar com a API");
            console.error(e);
            return;
        }

        console.log("Resposta da API:", data);

        if (!data || data.success !== true) {
            alert("Erro no backend ou dados inválidos.");
            return;
        }

        const motivos = Array.isArray(data.motivos) ? data.motivos : [];
        const dados = Array.isArray(data.dados) ? data.dados : [];

        if (dados.length === 0) {
            alert("Nenhum dado retornado pelo backend.");
            return;
        }

        // Mostrar área
        document.getElementById('relatorio-sup-info').style.display = 'block';
        document.getElementById('container-tabela-sup').style.display = 'block';

        document.getElementById('sup-periodo').textContent =
            `${data.periodo?.inicio || ''} até ${data.periodo?.fim || ''}`;

        document.getElementById('sup-total-registros').textContent = data.total_geral || 0;

        const thead = document.getElementById('cabecalho-supervisor');
        const tbody = document.querySelector('#tabela-supervisor tbody');

        // =========================
        // CABEÇALHO
        // =========================
        thead.innerHTML = '';
        thead.appendChild(criarTh('SUPERVISOR'));
        thead.appendChild(criarTh('PRESENTE'));

        motivos.forEach(m => thead.appendChild(criarTh(m)));
        thead.appendChild(criarTh('TOTAL'));

        // =========================
        // CORPO
        // =========================
        tbody.innerHTML = '';

        let totalPresentes = 0;
        let totalGeral = 0;
        const totalMotivos = {};
        motivos.forEach(m => totalMotivos[m] = 0);

        dados.forEach(item => {

            const tr = document.createElement('tr');
            const cont = item.contadores || {};

            const presentes = cont['PRESENTE'] || 0;
            totalPresentes += presentes;

            tr.appendChild(criarTd(item.supervisor || '---', true));
            tr.appendChild(criarTd(presentes));

            motivos.forEach(m => {
                const valor = cont[m] || 0;
                totalMotivos[m] += valor;
                tr.appendChild(criarTd(valor));
            });

            tr.appendChild(criarTd(item.total_registros || 0, true));
            totalGeral += item.total_registros || 0;

            tbody.appendChild(tr);
        });

        // =========================
        // TOTAL
        // =========================
        const trTotal = document.createElement('tr');
        trTotal.classList.add('linha-total');

        trTotal.appendChild(criarTd('TOTAL', true));
        trTotal.appendChild(criarTd(totalPresentes, true));

        motivos.forEach(m => trTotal.appendChild(criarTd(totalMotivos[m], true)));
        trTotal.appendChild(criarTd(totalGeral, true));

        tbody.appendChild(trTotal);

        document.getElementById('data-geracao').textContent = new Date().toLocaleString('pt-BR');
    }

    function criarTh(txt) {
        const th = document.createElement('th');
        th.textContent = txt;
        return th;
    }

    function criarTd(txt, bold = false) {
        const td = document.createElement('td');
        td.innerHTML = bold ? `<strong>${txt}</strong>` : txt;
        return td;
    }
});


