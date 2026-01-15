// ==========================================
// GESTÃO DE USUÁRIOS - JAVASCRIPT
// ==========================================

// Toggle Status (Ativar/Desativar)
async function toggleStatus(userId, novoStatus) {
    const acao = novoStatus ? 'ativar' : 'desativar';
    
    if (!confirm(`Tem certeza que deseja ${acao} este usuário?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/usuarios/toggle-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                ativo: novoStatus
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`✅ ${result.mensagem}`);
            window.location.reload();
        } else {
            alert(`❌ Erro: ${result.erro}`);
        }
        
    } catch (error) {
        alert('❌ Erro ao atualizar status: ' + error.message);
    }
}

// Resetar Senha
async function resetarSenha(userId, nomeUsuario) {
    const novaSenha = prompt(`🔑 Digite a nova senha para ${nomeUsuario}:\n\n(Mínimo 6 caracteres)`);
    
    if (!novaSenha) {
        return;
    }
    
    if (novaSenha.length < 6) {
        alert('❌ A senha deve ter no mínimo 6 caracteres!');
        return;
    }
    
    const confirmacao = prompt('Digite a senha novamente para confirmar:');
    
    if (novaSenha !== confirmacao) {
        alert('❌ As senhas não coincidem!');
        return;
    }
    
    try {
        const response = await fetch('/api/usuarios/resetar-senha', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                nova_senha: novaSenha
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`✅ ${result.mensagem}`);
        } else {
            alert(`❌ Erro: ${result.erro}`);
        }
        
    } catch (error) {
        alert('❌ Erro ao resetar senha: ' + error.message);
    }
}
