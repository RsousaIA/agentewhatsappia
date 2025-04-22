# Stub para modelos SQL - desabilitado temporariamente para permitir execução do sistema
# devido a incompatibilidade com Python 3.13

# Enums para status
class ConversaStatus:
    NOVO = 'novo'
    ATIVO = 'ativo'
    ENCERRADA = 'encerrada'
    REABERTA = 'reaberta'

class SolicitacaoStatus:
    PENDENTE = 'pendente'
    EM_ANDAMENTO = 'em_andamento'
    CONCLUIDA = 'concluida'
    CANCELADA = 'cancelada'
    ATRASADA = 'atrasada'

class AvaliacaoStatus:
    NAO_AVALIADA = 'nao_avaliada'
    AVALIADA = 'avaliada'
    REAVALIAR = 'reavaliar'

# Classes stub para os modelos
class Conversa:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.cliente_id = kwargs.get('cliente_id')
        self.status = kwargs.get('status', ConversaStatus.NOVO)
        self.data_hora_inicio = kwargs.get('data_hora_inicio')
        self.data_hora_fim = kwargs.get('data_hora_fim')
        self.foi_reaberta = kwargs.get('foi_reaberta', False)
        self.agentes_envolvidos = kwargs.get('agentes_envolvidos', [])
        self.tempo_total = kwargs.get('tempo_total', 0)
        self.tempo_resposta_medio = kwargs.get('tempo_resposta_medio', 0)
        self.ultima_mensagem = kwargs.get('ultima_mensagem')

class Mensagem:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.conversa_id = kwargs.get('conversa_id')
        self.tipo = kwargs.get('tipo', 'texto')
        self.conteudo = kwargs.get('conteudo', '')
        self.remetente = kwargs.get('remetente')
        self.timestamp = kwargs.get('timestamp')
        self.lida = kwargs.get('lida', False)
        self.url_midia = kwargs.get('url_midia')
        self.metadata = kwargs.get('metadata', {})

class Solicitacao:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.conversa_id = kwargs.get('conversa_id')
        self.descricao = kwargs.get('descricao', '')
        self.status = kwargs.get('status', SolicitacaoStatus.PENDENTE)
        self.data_criacao = kwargs.get('data_criacao')
        self.data_conclusao = kwargs.get('data_conclusao')
        self.prazo_prometido = kwargs.get('prazo_prometido')
        self.agente_responsavel = kwargs.get('agente_responsavel')
        self.prioridade = kwargs.get('prioridade', 'media')

class Avaliacao:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.conversa_id = kwargs.get('conversa_id')
        self.data_avaliacao = kwargs.get('data_avaliacao')
        self.nota_comunicacao_clara = kwargs.get('nota_comunicacao_clara', 0)
        self.nota_conhecimento_tecnico = kwargs.get('nota_conhecimento_tecnico', 0)
        self.nota_empatia_cordialidade = kwargs.get('nota_empatia_cordialidade', 0)
        self.nota_profissionalismo_etica = kwargs.get('nota_profissionalismo_etica', 0)
        self.nota_orientacao_resultados = kwargs.get('nota_orientacao_resultados', 0)
        self.nota_inteligencia_emocional = kwargs.get('nota_inteligencia_emocional', 0)
        self.nota_cumprimento_prazos = kwargs.get('nota_cumprimento_prazos', 0)
        self.nota_geral = kwargs.get('nota_geral', 0)
        self.reclamacoes = kwargs.get('reclamacoes', [])
        self.zerou_por_cordialidade = kwargs.get('zerou_por_cordialidade', False)
        self.detalhes_criticos = kwargs.get('detalhes_criticos', '')

class ConsolidadaAtendimento:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.conversa_id = kwargs.get('conversa_id')
        self.cliente_nome = kwargs.get('cliente_nome', '')
        self.agentes_envolvidos = kwargs.get('agentes_envolvidos', [])
        self.data_hora_inicio = kwargs.get('data_hora_inicio')
        self.data_hora_encerramento = kwargs.get('data_hora_encerramento')
        self.nota_geral = kwargs.get('nota_geral', 0)
        self.status_final = kwargs.get('status_final', '')
        self.resumo_final = kwargs.get('resumo_final', '') 