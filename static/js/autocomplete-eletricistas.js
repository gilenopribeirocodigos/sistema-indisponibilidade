// Autocomplete para campo de eletricistas
class AutocompleteEletricistas {
    constructor(inputId) {
        this.input = document.getElementById(inputId);
        this.sugestoes = null;
        this.debounceTimer = null;
        this.eletricistaSelecionado = null;
        
        this.init();
    }
    
    init() {
        // Criar elemento de sugestões
        this.criarElementoSugestoes();
        
        // Adicionar eventos
        this.input.addEventListener('input', (e) => this.handleInput(e));
        this.input.addEventListener('focus', (e) => this.handleFocus(e));
        
        // Fechar ao clicar fora
        document.addEventListener('click', (e) => {
            if (!this.input.contains(e.target) && !this.sugestoes.contains(e.target)) {
                this.fecharSugestoes();
            }
        });
    }
    
    criarElementoSugestoes() {
        // Criar div de sugestões
        this.sugestoes = document.createElement('div');
        this.sugestoes.className = 'autocomplete-sugestoes';
        this.sugestoes.style.display = 'none';
        
        // Inserir após o input
        this.input.parentNode.style.position = 'relative';
        this.input.parentNode.appendChild(this.sugestoes);
    }
    
    handleInput(e) {
        const valor = e.target.value.trim();
        
        // Limpar timer anterior
        clearTimeout(this.debounceTimer);
        
        // Limpar seleção anterior se usuário está digitando
        this.eletricistaSelecionado = null;
        this.limparCamposAutomaticos();
        
        // Se menos de 3 caracteres, fechar sugestões
        if (valor.length < 3) {
            this.fecharSugestoes();
            return;
        }
        
        // Buscar com delay (debounce)
        this.debounceTimer = setTimeout(() => {
            this.buscarEletricistas(valor);
        }, 300);
    }
    
    handleFocus(e) {
        // Se já tem valor e já buscou antes, mostrar sugestões novamente
        if (this.input.value.length >= 3 && this.sugestoes.children.length > 0) {
            this.sugestoes.style.display = 'block';
        }
    }
    
    async buscarEletricistas(termo) {
        try {
            // Fazer requisição à API
            const response = await fetch(`/api/buscar-eletricistas?q=${encodeURIComponent(termo)}`);
            const data = await response.json();
            
            // Mostrar resultados
            this.mostrarSugestoes(data.eletricistas);
            
        } catch (error) {
            console.error('Erro ao buscar eletricistas:', error);
        }
    }
    
    mostrarSugestoes(eletricistas) {
        // Limpar sugestões anteriores
        this.sugestoes.innerHTML = '';
        
        // Se não encontrou ninguém
        if (eletricistas.length === 0) {
            this.sugestoes.innerHTML = '<div class="autocomplete-item autocomplete-vazio">Nenhum eletricista encontrado</div>';
            this.sugestoes.style.display = 'block';
            return;
        }
        
        // Criar item para cada eletricista
        eletricistas.forEach(elet => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.innerHTML = `
                <div class="autocomplete-nome">${elet.nome}</div>
                <div class="autocomplete-detalhes">
                    Mat: ${elet.matricula} | Base: ${elet.base}
                </div>
            `;
            
            // Ao clicar, selecionar
            item.addEventListener('click', () => {
                this.selecionarEletricista(elet);
            });
            
            this.sugestoes.appendChild(item);
        });
        
        // Mostrar sugestões
        this.sugestoes.style.display = 'block';
    }
    
    selecionarEletricista(elet) {
        // Guardar eletricista selecionado
        this.eletricistaSelecionado = elet;
        
        // Preencher campo de nome
        this.input.value = elet.nome;
        
        // Preencher campos automáticos
        document.getElementById('matricula').value = elet.matricula;
        document.getElementById('base').value = elet.base;
        
        // Se o prefixo estiver vazio, sugerir o prefixo do eletricista
        const campoPrefixo = document.getElementById('prefixo');
        if (!campoPrefixo.value) {
            campoPrefixo.value = elet.prefixo;
        }
        
        // Fechar sugestões
        this.fecharSugestoes();
        
        // Focar no próximo campo (prefixo)
        campoPrefixo.focus();
        campoPrefixo.select();
    }
    
    limparCamposAutomaticos() {
        document.getElementById('matricula').value = '';
        document.getElementById('base').value = '';
    }
    
    fecharSugestoes() {
        this.sugestoes.style.display = 'none';
    }
}

// Inicializar quando a página carregar
document.addEventListener('DOMContentLoaded', () => {
    new AutocompleteEletricistas('colaborador');
});