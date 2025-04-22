import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Box, 
  Typography, 
  Paper, 
  TextField, 
  Button, 
  CircularProgress,
  Divider,
  IconButton,
  Avatar,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Tooltip
} from '@mui/material';
import { 
  Send as SendIcon,
  AttachFile as AttachIcon,
  ArrowBack as BackIcon,
  Phone as PhoneIcon,
  Image as ImageIcon,
  Mic as MicIcon,
  VideoLibrary as VideoIcon,
  Assessment as AssessmentIcon,
  Close as CloseIcon
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

import { 
  getConversationById, 
  getMessagesForConversation, 
  listenToMessages, 
  sendMessage,
  updateConversation 
} from '../services/firebase';

const statusColors = {
  'ACTIVE': 'primary',
  'CLOSED': 'success',
  'pending': 'warning',
  'escalated': 'error'
};

const MessageBubble = ({ message, isCurrentUser }) => {
  const getMessageTypeIcon = (type) => {
    switch (type) {
      case 'imagem':
        return <ImageIcon fontSize="small" />;
      case 'audio':
        return <MicIcon fontSize="small" />;
      case 'video':
        return <VideoIcon fontSize="small" />;
      default:
        return null;
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isCurrentUser ? 'flex-end' : 'flex-start',
        mb: 2,
      }}
    >
      {!isCurrentUser && (
        <Avatar 
          sx={{ 
            bgcolor: message.remetente === 'sistema' ? 'grey.500' : 'primary.main',
            width: 32,
            height: 32,
            mr: 1
          }}
        >
          {message.remetente === 'sistema' ? 'S' : 'C'}
        </Avatar>
      )}

      <Box>
        <Paper
          elevation={1}
          sx={{
            p: 1.5,
            maxWidth: '80%',
            borderRadius: 2,
            backgroundColor: isCurrentUser 
              ? 'primary.main' 
              : message.remetente === 'sistema'
                ? 'grey.200'
                : 'background.paper',
            color: isCurrentUser ? 'white' : 'text.primary',
            borderTopRightRadius: isCurrentUser ? 0 : 2,
            borderTopLeftRadius: isCurrentUser ? 2 : 0,
          }}
        >
          {message.tipo !== 'texto' && (
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              {getMessageTypeIcon(message.tipo)}
              <Typography variant="caption" sx={{ ml: 0.5 }}>
                {message.tipo === 'imagem' && 'Imagem'}
                {message.tipo === 'audio' && 'Áudio'}
                {message.tipo === 'video' && 'Vídeo'}
                {message.tipo === 'arquivo' && 'Arquivo'}
              </Typography>
            </Box>
          )}
          
          <Typography variant="body1">
            {message.conteudo}
          </Typography>
          
          {message.url_midia && (
            message.tipo === 'imagem' ? (
              <Box
                component="img"
                src={message.url_midia}
                alt="Imagem anexada"
                sx={{ 
                  maxWidth: '100%', 
                  maxHeight: '200px', 
                  mt: 1, 
                  borderRadius: 1 
                }}
              />
            ) : (
              <Button 
                size="small" 
                variant="outlined" 
                startIcon={getMessageTypeIcon(message.tipo)} 
                sx={{ mt: 1 }}
                href={message.url_midia}
                target="_blank"
              >
                Ver Anexo
              </Button>
            )
          )}
        </Paper>
        
        <Typography 
          variant="caption" 
          color="text.secondary" 
          sx={{ 
            display: 'block', 
            mt: 0.5,
            textAlign: isCurrentUser ? 'right' : 'left'
          }}
        >
          {message.timestamp?.toDate 
            ? formatDistanceToNow(new Date(message.timestamp.toDate()), { addSuffix: true, locale: ptBR }) 
            : '-'}
        </Typography>
      </Box>
      
      {isCurrentUser && (
        <Avatar 
          sx={{ 
            bgcolor: 'primary.dark', 
            width: 32, 
            height: 32, 
            ml: 1 
          }}
        >
          A
        </Avatar>
      )}
    </Box>
  );
};

const ConversationDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);
  
  useEffect(() => {
    const fetchConversation = async () => {
      try {
        setLoading(true);
        const conversationData = await getConversationById(id);
        setConversation(conversationData);
        
        // Buscar mensagens iniciais
        const initialMessages = await getMessagesForConversation(id);
        setMessages(initialMessages);
        
        setLoading(false);
      } catch (error) {
        console.error('Erro ao buscar conversa:', error);
        setLoading(false);
      }
    };
    
    fetchConversation();
    
    // Listener para atualizações em tempo real
    const unsubscribe = listenToMessages(id, (updatedMessages) => {
      setMessages(updatedMessages);
    });
    
    return () => {
      unsubscribe();
    };
  }, [id]);
  
  useEffect(() => {
    // Scroll para a última mensagem
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!newMessage.trim()) return;
    
    try {
      setSending(true);
      
      await sendMessage(id, {
        tipo: 'texto',
        conteudo: newMessage,
        remetente: 'atendente',
      });
      
      setNewMessage('');
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
    } finally {
      setSending(false);
    }
  };
  
  const handleCloseConversation = async () => {
    try {
      await updateConversation(id, {
        status: 'CLOSED',
        dataHoraFim: new Date()
      });
      
      // Adicionar mensagem de sistema
      await sendMessage(id, {
        tipo: 'sistema',
        conteudo: 'Conversa encerrada pelo atendente.',
        remetente: 'sistema'
      });
      
      // Atualizar o estado local
      setConversation({
        ...conversation,
        status: 'CLOSED'
      });
    } catch (error) {
      console.error('Erro ao encerrar conversa:', error);
    }
  };
  
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }
  
  if (!conversation) {
    return (
      <Box sx={{ textAlign: 'center', p: 4 }}>
        <Typography variant="h6" color="text.secondary">
          Conversa não encontrada
        </Typography>
        <Button
          startIcon={<BackIcon />}
          onClick={() => navigate(-1)}
          sx={{ mt: 2 }}
        >
          Voltar
        </Button>
      </Box>
    );
  }
  
  const isActive = conversation.status === 'ACTIVE';
  
  return (
    <Box>
      <Paper elevation={1} sx={{ mb: 3, p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <IconButton onClick={() => navigate(-1)} sx={{ mr: 1 }}>
              <BackIcon />
            </IconButton>
            
            <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
              {(conversation.cliente?.nome || 'C')[0].toUpperCase()}
            </Avatar>
            
            <Box>
              <Typography variant="h6">
                {conversation.cliente?.nome || conversation.cliente?.telefone || 'Cliente'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {conversation.cliente?.telefone || ''}
              </Typography>
            </Box>
          </Box>
          
          <Box>
            <Chip 
              label={conversation.status === 'ACTIVE' ? 'Ativa' : 'Encerrada'} 
              color={statusColors[conversation.status] || 'default'} 
              size="small" 
              sx={{ mr: 1 }}
            />
            
            <Tooltip title="Ver Avaliação">
              <IconButton color="primary">
                <AssessmentIcon />
              </IconButton>
            </Tooltip>
            
            <Tooltip title="Ligar">
              <IconButton color="primary">
                <PhoneIcon />
              </IconButton>
            </Tooltip>
            
            {isActive && (
              <Tooltip title="Encerrar Conversa">
                <IconButton color="error" onClick={handleCloseConversation}>
                  <CloseIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>
      </Paper>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card sx={{ height: '75vh', display: 'flex', flexDirection: 'column' }}>
            <CardHeader 
              title="Conversa" 
              subheader={`Iniciada em: ${conversation.dataHoraInicio?.toDate 
                ? new Date(conversation.dataHoraInicio.toDate()).toLocaleString('pt-BR') 
                : '-'}`}
            />
            <Divider />
            
            <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto' }}>
              {messages.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', p: 4 }}>
                  Nenhuma mensagem nesta conversa
                </Typography>
              ) : (
                messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    isCurrentUser={message.remetente === 'atendente'}
                  />
                ))
              )}
              <div ref={messagesEndRef} />
            </Box>
            
            <Divider />
            
            <Box sx={{ p: 2 }}>
              <form onSubmit={handleSendMessage}>
                <Box sx={{ display: 'flex' }}>
                  <IconButton disabled={!isActive}>
                    <AttachIcon />
                  </IconButton>
                  
                  <TextField
                    fullWidth
                    placeholder={isActive ? "Digite sua mensagem..." : "Conversa encerrada"}
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    variant="outlined"
                    size="small"
                    disabled={!isActive || sending}
                  />
                  
                  <Button
                    type="submit"
                    color="primary"
                    variant="contained"
                    disabled={!isActive || sending || !newMessage.trim()}
                    sx={{ ml: 1 }}
                  >
                    {sending ? <CircularProgress size={24} /> : <SendIcon />}
                  </Button>
                </Box>
              </form>
            </Box>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Card>
            <CardHeader title="Detalhes do Cliente" />
            <Divider />
            <CardContent>
              <Typography variant="body2">
                <strong>Nome:</strong> {conversation.cliente?.nome || 'Não informado'}
              </Typography>
              <Typography variant="body2">
                <strong>Telefone:</strong> {conversation.cliente?.telefone || 'Não informado'}
              </Typography>
              <Typography variant="body2">
                <strong>Status:</strong> {conversation.status === 'ACTIVE' ? 'Ativa' : 'Encerrada'}
              </Typography>
              <Typography variant="body2">
                <strong>Início:</strong> {conversation.dataHoraInicio?.toDate 
                  ? new Date(conversation.dataHoraInicio.toDate()).toLocaleString('pt-BR') 
                  : '-'}
              </Typography>
              {conversation.dataHoraFim && (
                <Typography variant="body2">
                  <strong>Encerramento:</strong> {conversation.dataHoraFim?.toDate 
                    ? new Date(conversation.dataHoraFim.toDate()).toLocaleString('pt-BR') 
                    : '-'}
                </Typography>
              )}
            </CardContent>
          </Card>
          
          <Card sx={{ mt: 3 }}>
            <CardHeader title="Avaliação" />
            <Divider />
            <CardContent>
              {conversation.avaliada ? (
                <>
                  <Typography variant="body2">
                    <strong>Nota Geral:</strong> {conversation.notaGeral || 'Não disponível'}
                  </Typography>
                  <Button 
                    variant="outlined" 
                    startIcon={<AssessmentIcon />} 
                    sx={{ mt: 2 }}
                    fullWidth
                  >
                    Ver Avaliação Completa
                  </Button>
                </>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Esta conversa ainda não foi avaliada.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ConversationDetail; 