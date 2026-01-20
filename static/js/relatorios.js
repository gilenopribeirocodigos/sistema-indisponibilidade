// ==========================================
// RELATÓRIOS - JAVASCRIPT
// ==========================================

document.addEventListener('DOMContentLoaded', () => {

    const btnGerar = document.getElementById('btn-gerar-relatorio');

    btnGerar.addEventListener('click', gerarRelatorioPorSupervisor);

    async function gerarRelatorioPorSupervisor() {

        const tipo = document.getElementById('tipo-periodo').value;
        let dataInicio, dataFim;

        if (tipo === 'dia') {
            dataInicio = document.getElementById('data-dia').value;
            dataFim = dataInicio;
        } else {
            dataInicio = document.getElementById('data-inicio').value;
            dataFim = document.getElementById('data-fim').value;
        }

        if (!dataInicio || !dataFim) {
            alert('Selecione o período');
            return;
        }

        const response = await fetch(`/api/relatorio-por-supervisor?data_inicio=${dataInicio}&data_fim=${dataFim}`);
        const data = await response.json();

        if (!data.success) {
            alert(data.erro);
            return;
        }

        document.getElementById('relatorio-sup-info').style.display = 'block';
        document.getElementById('container-tabela-sup').style.display = 'block';

        document.getElementById('sup-periodo').textContent =
            `${data.periodo.inicio} até ${data.periodo.fim} (${data.periodo.dias} dia(s))`;

        document.getElementById('sup-total-registros').textContent = data.total_geral;

        const motivos = data.motivos;
        const tbody = document.querySelector('#tabela-supervisor tbody');
        const thead = document.getElementById('cabecalho-supervisor');

        // ===== CABEÇALHO =====
        thead.innerHTML = '';

        thead.appendChild(criarTh('SUPERVISOR'));
        thead.appendChild(criarTh('PRESENTE'));

        motivos.forEach(m => {
            thead.appendChild(criarTh(m));
        });

        thead.appendChild(criarTh('TOTAL'));

        // ===== DADOS =====
        tbody.innerHTML = '';

        let totalPresentes = 0;
        let totalGeral = 0;
        const totalMotivos = {};
        motivos.forEach(m => totalMotivos[m] = 0);

        data.dados.forEach(item => {

            const tr = document.createElement('tr');
            const cont = item.contadores || {};

            const presentes = cont['PRESENTE'] || 0;
            totalPresentes += presentes;

            tr.appendChild(criarTd(item.supervisor, true));
            tr.appendChild(criarTd(presentes));

            motivos.forEach(m => {
                const valor = cont[m] || 0;
                totalMotivos[m] += valor;
                tr.appendChild(criarTd(valor));
            });

            tr.appendChild(criarTd(item.total_registros, true));
            totalGeral += item.total_registros;

            tbody.appendChild(tr);
        });

        // ===== LINHA TOTAL =====
        const trTotal = document.createElement('tr');
        trTotal.classList.add('linha-total');

        trTotal.appendChild(criarTd('TOTAL', true));
        trTotal.appendChild(criarTd(totalPresentes, true));

        motivos.forEach(m => {
            trTotal.appendChild(criarTd(totalMotivos[m], true));
        });

        trTotal.appendChild(criarTd(totalGeral, true));
        tbody.appendChild(trTotal);

        document.getElementById('data-geracao').textContent = new Date().toLocaleString('pt-BR');
    }

    function criarTh(texto) {
        const th = document.createElement('th');
        th.textContent = texto;
        return th;
    }

    function criarTd(texto, bold = false) {
        const td = document.createElement('td');
        td.innerHTML = bold ? `<strong>${texto}</strong>` : texto;
        return td;
    }
});

