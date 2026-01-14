// Autocomplete para campo de prefixos
class AutocompletePrefixos {
    constructor(inputId) {
        this.input = document.getElementById(inputId);
        this.sugestoes = null;
        this.debounceTimer = null;
        
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
        
        // Se menos de 3 caracteres, fechar sugestões
        if (valor.length < 3) {
            this.fecharSugestoes();
            return;
        }
        
        // Buscar com delay (debounce)
        this.debounceTimer = setTimeout(() => {
            this.buscarPrefixos(valor);
        }, 300);
    }
    
    handleFocus(e) {
        // Se já tem valor e já buscou antes, mostrar sugestões novamente
        if (this.input.value.length >= 3 && this.sugestoes.children.length > 0) {
            this.sugestoes.style.display = 'block';
        }
    }
    
    async buscarPrefixos(termo) {
        try {
            // Fazer requisição à API
            const response = await fetch(`/api/buscar-prefixos?q=${encodeURIComponent(termo)}`);
            const data = await response.json();
            
            // Mostrar resultados
            this.mostrarSugestoes(data.prefixos);
            
        } catch (error) {
            console.error('Erro ao buscar prefixos:', error);
        }
    }
    
    mostrarSugestoes(prefixos) {
        // Limpar sugestões anteriores
        this.sugestoes.innerHTML = '';
        
        // Se não encontrou nenhum
        if (prefixos.length === 0) {
            this.sugestoes.innerHTML = '<div class="autocomplete-item autocomplete-vazio">Nenhum prefixo encontrado</div>';
            this.sugestoes.style.display = 'block';
            return;
        }
        
        // Criar item para cada prefixo
        prefixos.forEach(pref => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.innerHTML = `
                <div class="autocomplete-nome">${pref.prefixo}</div>
                <div class="autocomplete-detalhes">
                    Base: ${pref.base} | ${pref.total_eletricistas} eletricista(s)
                </div>
            `;
            
            // Ao clicar, selecionar
            item.addEventListener('click', () => {
                this.selecionarPrefixo(pref);
            });
            
            this.sugestoes.appendChild(item);
        });
        
        // Mostrar sugestões
        this.sugestoes.style.display = 'block';
    }
    
    selecionarPrefixo(pref) {
        // Preencher campo de prefixo
        this.input.value = pref.prefixo;
        
        // Fechar sugestões
        this.fecharSugestoes();
        
        // Focar no próximo campo (motivo)
        const campoMotivo = document.getElementById('motivo_id');
        if (campoMotivo) {
            campoMotivo.focus();
        }
    }
    
    fecharSugestoes() {
        this.sugestoes.style.display = 'none';
    }
}

// Inicializar quando a página carregar
document.addEventListener('DOMContentLoaded', () => {
    new AutocompletePrefixos('prefixo');
});