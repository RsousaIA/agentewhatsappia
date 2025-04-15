// Inicialização do Socket.IO
const socket = io();

// Mapa de cores para gráficos
const chartColors = {
    primary: '#4e73df',
    success: '#1cc88a',
    info: '#36b9cc',
    warning: '#f6c23e',
    danger: '#e74a3b',
    dark: '#5a5c69',
    primaryLight: 'rgba(78, 115, 223, 0.2)',
    successLight: 'rgba(28, 200, 138, 0.2)',
    infoLight: 'rgba(54, 185, 204, 0.2)',
    warningLight: 'rgba(246, 194, 62, 0.2)',
    dangerLight: 'rgba(231, 74, 59, 0.2)'
};

// Referências aos elementos HTML
const conversasAtivas = document.getElementById('conversas-ativas');
const mensagensHoje = document.getElementById('mensagens-hoje');
const solicitacoesPendentes = document.getElementById('solicitacoes-pendentes');
const notaMedia = document.getElementById('nota-media');
const currentTime = document.getElementById('current-time');
const statusText = document.getElementById('status-text');

// Referências às seções
const sections = document.querySelectorAll('.section');
const navLinks = document.querySelectorAll('.nav-link');

// Referências aos modais
const conversaModal = document.getElementById('conversa-modal');
const avaliacaoModal = document.getElementById('avaliacao-modal');
const closeConversaModal = document.getElementById('close-conversa-modal');
const closeAvaliacaoModal = document.getElementById('close-avaliacao-modal');
const conversaModalBody = document.getElementById('conversa-modal-body');
const avaliacaoModalBody = document.getElementById('avaliacao-modal-body');

// Referências às tabelas
const avaliacoesRecentes = document.getElementById('avaliacoes-recentes');
const conversasTable = document.getElementById('conversas-table');
const solicitacoesTable = document.getElementById('solicitacoes-table');
const avaliacoesTable = document.getElementById('avaliacoes-table');

// Gráficos
let mensagensChart;
let solicitacoesChart;
let tempoRespostaChart;

// Armazenamento de dados
let dashboardData = {};
let conversasData = [];
let solicitacoesData = [];
let avaliacoesData = [];

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    initCharts();
    loadDashboardData();
    setInterval(loadDashboardData, 30000);
    
    // Inicialização da navegação
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetSection = link.getAttribute('data-section');
            changeSection(targetSection);
        });
    });
    
    // Inicialização dos modais
    closeConversaModal.addEventListener('click', () => {
        conversaModal.classList.remove('show');
    });
    
    closeAvaliacaoModal.addEventListener('click', () => {
        avaliacaoModal.classList.remove('show');
    });
    
    // Eventos de socket
    socket.on('connect', () => {
        statusText.textContent = 'Conectado';
        statusText.classList.remove('offline');
        statusText.classList.add('online');
    });
    
    socket.on('disconnect', () => {
        statusText.textContent = 'Desconectado';
        statusText.classList.remove('online');
        statusText.classList.add('offline');
    });
    
    socket.on('stats', (data) => {
        updateStats(data);
    });
});

// Funções de atualização
function updateCurrentTime() {
    const now = new Date();
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    };
    currentTime.textContent = now.toLocaleDateString('pt-BR', options);
}

function changeSection(sectionId) {
    // Esconder todas as seções
    sections.forEach(section => {
        section.classList.remove('active');
    });
    
    // Desativar todos os links
    navLinks.forEach(link => {
        link.classList.remove('active');
    });
    
    // Mostrar a seção alvo
    document.getElementById(sectionId).classList.add('active');
    
    // Ativar o link correspondente
    document.querySelector(`.nav-link[data-section="${sectionId}"]`).classList.add('active');
    
    // Carregar dados específicos da seção
    if (sectionId === 'conversas') {
        loadConversas();
    } else if (sectionId === 'solicitacoes') {
        loadSolicitacoes();
    } else if (sectionId === 'avaliacoes') {
        loadAvaliacoes();
    } else if (sectionId === 'metricas') {
        loadMetricas();
    }
}

// Inicialização de gráficos
function initCharts() {
    // Gráfico de mensagens por dia
    const mensagensCtx = document.getElementById('mensagensChart').getContext('2d');
    mensagensChart = new Chart(mensagensCtx, {
        type: 'bar',
        data: {
            labels: ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
            datasets: [{
                label: 'Mensagens',
                data: [0, 0, 0, 0, 0, 0, 0],
                backgroundColor: chartColors.primaryLight,
                borderColor: chartColors.primary,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
    
    // Gráfico de status de solicitações
    const solicitacoesCtx = document.getElementById('solicitacoesChart').getContext('2d');
    solicitacoesChart = new Chart(solicitacoesCtx, {
        type: 'doughnut',
        data: {
            labels: ['Pendente', 'Atendida', 'Atrasada', 'Não Atendida'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [
                    chartColors.warning,
                    chartColors.success,
                    chartColors.danger,
                    chartColors.dark
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
    
    // Gráfico de tempo de resposta
    const tempoRespostaCtx = document.getElementById('tempoRespostaChart').getContext('2d');
    tempoRespostaChart = new Chart(tempoRespostaCtx, {
        type: 'bar',
        data: {
            labels: ['Médio', 'Máximo'],
            datasets: [{
                label: 'Tempo (s)',
                data: [0, 0],
                backgroundColor: [
                    chartColors.info,
                    chartColors.danger
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Carregamento de dados
async function loadDashboardData() {
    try {
        const response = await fetch('/api/dashboard');
        if (!response.ok) {
            throw new Error('Erro ao carregar dados do dashboard');
        }
        
        dashboardData = await response.json();
        updateStats(dashboardData);
        updateCharts(dashboardData);
        updateAvaliacoesRecentes(dashboardData.avaliacoes_recentes);
    } catch (error) {
        console.error('Erro ao carregar dados:', error);
    }
}

async function loadConversas() {
    try {
        const response = await fetch('/api/conversas');
        if (!response.ok) {
            throw new Error('Erro ao carregar conversas');
        }
        
        conversasData = await response.json();
        updateConversasTable(conversasData);
    } catch (error) {
        console.error('Erro ao carregar conversas:', error);
    }
}

async function loadSolicitacoes() {
    try {
        const response = await fetch('/api/solicitacoes');
        if (!response.ok) {
            throw new Error('Erro ao carregar solicitações');
        }
        
        solicitacoesData = await response.json();
        updateSolicitacoesTable(solicitacoesData);
    } catch (error) {
        console.error('Erro ao carregar solicitações:', error);
    }
}

async function loadAvaliacoes() {
    try {
        const response = await fetch('/api/avaliacoes');
        if (!response.ok) {
            throw new Error('Erro ao carregar avaliações');
        }
        
        avaliacoesData = await response.json();
        updateAvaliacoesTable(avaliacoesData);
    } catch (error) {
        console.error('Erro ao carregar avaliações:', error);
    }
}

function loadMetricas() {
    // Esta função será implementada mais tarde
    const metricasContent = document.getElementById('metricas-content');
    
    // Mostrar dados de métricas usando os dados do dashboard
    if (dashboardData && Object.keys(dashboardData).length > 0) {
        metricasContent.innerHTML = `
            <div style="margin-bottom: 2rem;">
                <h4>Métricas de Atendimento</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; margin-top: 1rem;">
                    <div class="metric-card">
                        <h5>Tempo Médio de Resposta</h5>
                        <p class="metric-value">${Math.round(dashboardData.tempo_medio_resposta)} segundos</p>
                    </div>
                    <div class="metric-card">
                        <h5>Tempo Máximo de Resposta</h5>
                        <p class="metric-value">${Math.round(dashboardData.tempo_maximo_resposta)} segundos</p>
                    </div>
                    <div class="metric-card">
                        <h5>Avaliações Realizadas</h5>
                        <p class="metric-value">${dashboardData.avaliacoes_feitas}</p>
                    </div>
                    <div class="metric-card">
                        <h5>Nota Média</h5>
                        <p class="metric-value">${dashboardData.nota_media.toFixed(1)}</p>
                    </div>
                </div>
            </div>
            
            <div>
                <h4>Distribuição de Status das Solicitações</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
                    <div class="metric-card">
                        <h5>Pendentes</h5>
                        <p class="metric-value">${dashboardData.status_solicitacoes.pendente}</p>
                    </div>
                    <div class="metric-card">
                        <h5>Atendidas</h5>
                        <p class="metric-value">${dashboardData.status_solicitacoes.atendida}</p>
                    </div>
                    <div class="metric-card">
                        <h5>Atrasadas</h5>
                        <p class="metric-value">${dashboardData.status_solicitacoes.atrasada}</p>
                    </div>
                    <div class="metric-card">
                        <h5>Não Atendidas</h5>
                        <p class="metric-value">${dashboardData.status_solicitacoes.nao_atendida}</p>
                    </div>
                </div>
            </div>
        `;
    }
}

// Atualização de elementos da interface
function updateStats(data) {
    conversasAtivas.textContent = data.conversas_ativas;
    mensagensHoje.textContent = data.mensagens_hoje;
    solicitacoesPendentes.textContent = data.solicitacoes_pendentes;
    
    if (data.nota_media) {
        notaMedia.textContent = data.nota_media.toFixed(1);
    } else {
        notaMedia.textContent = '0.0';
    }
}

function updateCharts(data) {
    // Atualizar gráfico de mensagens por dia
    if (data.mensagens_por_dia && data.mensagens_por_dia.length > 0) {
        mensagensChart.data.labels = data.mensagens_por_dia.map(item => item.data);
        mensagensChart.data.datasets[0].data = data.mensagens_por_dia.map(item => item.quantidade);
        mensagensChart.update();
    }
    
    // Atualizar gráfico de status das solicitações
    if (data.status_solicitacoes) {
        solicitacoesChart.data.datasets[0].data = [
            data.status_solicitacoes.pendente,
            data.status_solicitacoes.atendida,
            data.status_solicitacoes.atrasada,
            data.status_solicitacoes.nao_atendida
        ];
        solicitacoesChart.update();
    }
    
    // Atualizar gráfico de tempo de resposta
    if (data.tempo_medio_resposta !== undefined && data.tempo_maximo_resposta !== undefined) {
        tempoRespostaChart.data.datasets[0].data = [
            Math.round(data.tempo_medio_resposta),
            Math.round(data.tempo_maximo_resposta)
        ];
        tempoRespostaChart.update();
    }
}

function updateAvaliacoesRecentes(avaliacoes) {
    if (!avaliacoes || avaliacoes.length === 0) {
        avaliacoesRecentes.querySelector('tbody').innerHTML = `
            <tr>
                <td colspan="5" class="text-center">Nenhuma avaliação encontrada</td>
            </tr>
        `;
        return;
    }
    
    const tbody = avaliacoesRecentes.querySelector('tbody');
    tbody.innerHTML = '';
    
    avaliacoes.forEach(avaliacao => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${avaliacao.cliente}</td>
            <td>${avaliacao.atendente}</td>
            <td>
                <div class="star-rating">
                    ${getStarRating(avaliacao.nota)}
                    <span class="rating-value">${avaliacao.nota.toFixed(1)}</span>
                </div>
            </td>
            <td>${avaliacao.data}</td>
            <td>
                <button class="btn btn-primary btn-sm" onclick="showAvaliacaoDetails(${avaliacao.id})">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function updateConversasTable(conversas) {
    if (!conversas || conversas.length === 0) {
        conversasTable.querySelector('tbody').innerHTML = `
            <tr>
                <td colspan="8" class="text-center">Nenhuma conversa encontrada</td>
            </tr>
        `;
        return;
    }
    
    const tbody = conversasTable.querySelector('tbody');
    tbody.innerHTML = '';
    
    conversas.forEach(conversa => {
        const tr = document.createElement('tr');
        
        // Determinar a classe de status
        let statusClass = '';
        if (conversa.status === 'ativo') {
            statusClass = 'active';
        } else if (conversa.status === 'finalizado') {
            statusClass = 'closed';
        } else if (conversa.status === 'reaberto') {
            statusClass = 'pending';
        }
        
        tr.innerHTML = `
            <td>${conversa.id}</td>
            <td>${conversa.cliente}</td>
            <td>${conversa.atendente}</td>
            <td><span class="status-badge ${statusClass}">${conversa.status}</span></td>
            <td>${conversa.inicio || '-'}</td>
            <td>${conversa.duracao || '-'}</td>
            <td>${conversa.tempo_resposta || '-'}</td>
            <td>
                <button class="btn btn-primary btn-sm" onclick="showConversaDetails(${conversa.id})">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function updateSolicitacoesTable(solicitacoes) {
    if (!solicitacoes || solicitacoes.length === 0) {
        solicitacoesTable.querySelector('tbody').innerHTML = `
            <tr>
                <td colspan="8" class="text-center">Nenhuma solicitação encontrada</td>
            </tr>
        `;
        return;
    }
    
    const tbody = solicitacoesTable.querySelector('tbody');
    tbody.innerHTML = '';
    
    solicitacoes.forEach(solicitacao => {
        const tr = document.createElement('tr');
        
        // Determinar a classe de status
        let statusClass = '';
        if (solicitacao.status === 'pendente') {
            statusClass = solicitacao.esta_atrasada ? 'late' : 'pending';
        } else if (solicitacao.status === 'atendida') {
            statusClass = 'active';
        } else if (solicitacao.status === 'atrasada') {
            statusClass = 'late';
        } else {
            statusClass = 'closed';
        }
        
        tr.innerHTML = `
            <td>${solicitacao.id}</td>
            <td>${solicitacao.cliente}</td>
            <td>${solicitacao.descricao}</td>
            <td>${solicitacao.data_solicitacao || '-'}</td>
            <td>${solicitacao.prazo_prometido || '-'}</td>
            <td><span class="status-badge ${statusClass}">${solicitacao.status}</span></td>
            <td>${solicitacao.atendente}</td>
            <td>
                <button class="btn btn-primary btn-sm" onclick="showConversaDetails(${solicitacao.conversa_id})">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function updateAvaliacoesTable(avaliacoes) {
    if (!avaliacoes || avaliacoes.length === 0) {
        avaliacoesTable.querySelector('tbody').innerHTML = `
            <tr>
                <td colspan="9" class="text-center">Nenhuma avaliação encontrada</td>
            </tr>
        `;
        return;
    }
    
    const tbody = avaliacoesTable.querySelector('tbody');
    tbody.innerHTML = '';
    
    avaliacoes.forEach(avaliacao => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${avaliacao.id}</td>
            <td>${avaliacao.cliente}</td>
            <td>${avaliacao.atendente}</td>
            <td>
                <div class="star-rating">
                    ${getStarRating(avaliacao.nota_final)}
                    <span class="rating-value">${avaliacao.nota_final.toFixed(1)}</span>
                </div>
            </td>
            <td>${avaliacao.clareza_comunicacao}</td>
            <td>${avaliacao.conhecimento_tecnico}</td>
            <td>${avaliacao.paciencia}</td>
            <td>${avaliacao.data_avaliacao}</td>
            <td>
                <button class="btn btn-primary btn-sm" onclick="showAvaliacaoDetails(${avaliacao.id})">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Funções auxiliares
function getStarRating(rating) {
    const fullStars = Math.floor(rating / 2);
    const halfStar = rating % 2 >= 1;
    const emptyStars = 5 - fullStars - (halfStar ? 1 : 0);
    
    let stars = '';
    
    for (let i = 0; i < fullStars; i++) {
        stars += '<i class="fas fa-star"></i>';
    }
    
    if (halfStar) {
        stars += '<i class="fas fa-star-half-alt"></i>';
    }
    
    for (let i = 0; i < emptyStars; i++) {
        stars += '<i class="far fa-star"></i>';
    }
    
    return stars;
}

// Funções para exibir detalhes
async function showConversaDetails(conversaId) {
    // Mostrar modal
    conversaModal.classList.add('show');
    conversaModalBody.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
        </div>
    `;
    
    try {
        const response = await fetch(`/api/conversa/${conversaId}`);
        if (!response.ok) {
            throw new Error('Erro ao carregar detalhes da conversa');
        }
        
        const data = await response.json();
        
        if (data.erro) {
            conversaModalBody.innerHTML = `
                <div class="alert alert-danger">
                    ${data.mensagem}
                </div>
            `;
            return;
        }
        
        // Formatar mensagens para exibição
        let mensagensHtml = '';
        if (data.mensagens && data.mensagens.length > 0) {
            mensagensHtml = `
                <h6>Conversa</h6>
                <div class="chat-container">
                    ${data.mensagens.map(msg => `
                        <div class="message ${msg.remetente === 'cliente' ? 'client' : 'attendant'}">
                            <div class="message-header">
                                <strong>${msg.nome}</strong>
                            </div>
                            <div class="message-content">${msg.conteudo}</div>
                            <div class="message-time">${msg.data_hora}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            mensagensHtml = `
                <div class="alert alert-info">
                    Nenhuma mensagem encontrada para esta conversa.
                </div>
            `;
        }
        
        // Formatar solicitações
        let solicitacoesHtml = '';
        if (data.solicitacoes && data.solicitacoes.length > 0) {
            solicitacoesHtml = `
                <h6 style="margin-top: 1.5rem;">Solicitações</h6>
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Descrição</th>
                                <th>Data</th>
                                <th>Prazo</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.solicitacoes.map(s => {
                                // Determinar a classe de status
                                let statusClass = '';
                                if (s.status === 'pendente') {
                                    statusClass = 'pending';
                                } else if (s.status === 'atendida') {
                                    statusClass = 'active';
                                } else if (s.status === 'atrasada') {
                                    statusClass = 'late';
                                } else {
                                    statusClass = 'closed';
                                }
                                
                                return `
                                    <tr>
                                        <td>${s.descricao}</td>
                                        <td>${s.data_solicitacao || '-'}</td>
                                        <td>${s.prazo_prometido || '-'}</td>
                                        <td><span class="status-badge ${statusClass}">${s.status}</span></td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        // Formatar avaliação
        let avaliacaoHtml = '';
        if (data.avaliacao) {
            avaliacaoHtml = `
                <h6 style="margin-top: 1.5rem;">Avaliação</h6>
                <div style="background-color: #f8f9fc; padding: 1rem; border-radius: 0.35rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
                        <div>
                            <strong>Nota Final:</strong>
                            <div class="star-rating">
                                ${getStarRating(data.avaliacao.nota_final)}
                                <span class="rating-value">${data.avaliacao.nota_final.toFixed(1)}</span>
                            </div>
                        </div>
                        <div>
                            <strong>Data:</strong> ${data.avaliacao.data_avaliacao}
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem;">
                        <div>
                            <strong>Comunicação:</strong> ${data.avaliacao.clareza_comunicacao}/10
                        </div>
                        <div>
                            <strong>Conhecimento:</strong> ${data.avaliacao.conhecimento_tecnico}/10
                        </div>
                        <div>
                            <strong>Paciência:</strong> ${data.avaliacao.paciencia}/10
                        </div>
                        <div>
                            <strong>Profissionalismo:</strong> ${data.avaliacao.profissionalismo}/10
                        </div>
                        <div>
                            <strong>Intel. Emocional:</strong> ${data.avaliacao.inteligencia_emocional}/10
                        </div>
                        <div>
                            <strong>Cumpr. Prazos:</strong> ${data.avaliacao.cumprimento_prazos}/10
                        </div>
                    </div>
                    
                    ${data.avaliacao.reclamacao_cliente ? `
                        <div style="margin-top: 1rem;">
                            <strong>Reclamações do Cliente:</strong>
                            <p style="margin-top: 0.5rem;">${data.avaliacao.reclamacao_cliente}</p>
                        </div>
                    ` : ''}
                    
                    ${data.avaliacao.observacoes ? `
                        <div style="margin-top: 1rem;">
                            <strong>Observações:</strong>
                            <p style="margin-top: 0.5rem;">${data.avaliacao.observacoes}</p>
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        // Montar HTML completo
        conversaModalBody.innerHTML = `
            <div>
                <h5>Informações da Conversa</h5>
                <div style="background-color: #f8f9fc; padding: 1rem; border-radius: 0.35rem; margin-bottom: 1.5rem;">
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem;">
                        <div>
                            <strong>Cliente:</strong> ${data.conversa.cliente}
                        </div>
                        <div>
                            <strong>Atendente:</strong> ${data.conversa.atendente}
                        </div>
                        <div>
                            <strong>Início:</strong> ${data.conversa.data_inicio || '-'}
                        </div>
                        <div>
                            <strong>Fim:</strong> ${data.conversa.data_fim || '-'}
                        </div>
                        <div>
                            <strong>Status:</strong> ${data.conversa.status}
                        </div>
                        <div>
                            <strong>Tempo Total:</strong> ${data.conversa.tempo_total ? `${Math.round(data.conversa.tempo_total / 60)} min` : '-'}
                        </div>
                        <div>
                            <strong>Tempo Médio Resposta:</strong> ${data.conversa.tempo_resposta_medio ? `${Math.round(data.conversa.tempo_resposta_medio)} s` : '-'}
                        </div>
                        <div>
                            <strong>Tempo Máx Resposta:</strong> ${data.conversa.tempo_resposta_maximo ? `${Math.round(data.conversa.tempo_resposta_maximo)} s` : '-'}
                        </div>
                    </div>
                </div>
                
                ${mensagensHtml}
                ${solicitacoesHtml}
                ${avaliacaoHtml}
            </div>
        `;
    } catch (error) {
        console.error('Erro ao carregar detalhes da conversa:', error);
        conversaModalBody.innerHTML = `
            <div class="alert alert-danger">
                Erro ao carregar detalhes da conversa: ${error.message}
            </div>
        `;
    }
}

async function showAvaliacaoDetails(avaliacaoId) {
    // Esta função será implementada mais tarde
    avaliacaoModal.classList.add('show');
    avaliacaoModalBody.innerHTML = `
        <div class="alert alert-info">
            Detalhes da avaliação ${avaliacaoId} estão sendo carregados.
        </div>
    `;
}

// Funções globais para eventos dos botões
window.showConversaDetails = showConversaDetails;
window.showAvaliacaoDetails = showAvaliacaoDetails; 