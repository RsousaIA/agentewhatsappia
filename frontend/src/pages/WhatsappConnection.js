import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Button, 
  CircularProgress,
  Divider,
  Alert,
  Card,
  CardContent,
  CardHeader,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import { 
  QrCode as QrCodeIcon,
  PhoneAndroid as PhoneIcon,
  Check as CheckIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  WhatsApp as WhatsAppIcon
} from '@mui/icons-material';

// Simulação de API para WhatsApp
const fetchWhatsAppStatus = () => {
  return new Promise((resolve) => {
    setTimeout(() => {
      // Simula uma resposta da API
      resolve({
        connected: false,
        qrCode: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIQAAACECAYAAABRRIOnAAAAAklEQVR4AewaftIAAAOPSURBVO3BQY7cSBAEwfAC//9l3znmqYBGJbVm2Az7g1rrfx62hlnDrGHWMGuYNcwaZg2zhlnDrGHWMGuYNcwaZg2zhlnDrGHWMGuYNcwaZg2zhvnwUgl+UuJOCU4SJwknCXdK3Ek4SbhTglcSP1PiTsJJwknCNx4Ns4ZZw6xh1jAfXlaCVyW8KuFOwkmJk4Q7CScl7iS8KuFVCa9KeFXCNx4Ns4ZZw6xh1jAfvqwEJwl3JU4STkrcSThJuJNwJ+FOwhsJr0q4k3CS8GcNs4ZZw6xh1jAfXirBT0p4I+FViZMSJwknJe4kvCrhVQnflHAn4U7CNx4Ns4ZZw6xh1jD/B3LrsNFe7YfeAAAAAElFTkSuQmCC',
        status: 'waiting_connection'
      });
    }, 1000);
  });
};

const WhatsappConnection = () => {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('disconnected');  // disconnected, connecting, connected, error
  const [qrCode, setQrCode] = useState(null);
  const [message, setMessage] = useState('');
  
  useEffect(() => {
    const checkWhatsAppStatus = async () => {
      try {
        setLoading(true);
        const data = await fetchWhatsAppStatus();
        
        if (data.connected) {
          setStatus('connected');
          setMessage('WhatsApp conectado com sucesso!');
        } else if (data.qrCode) {
          setStatus('connecting');
          setQrCode(data.qrCode);
          setMessage('Escaneie o código QR para conectar');
        } else {
          setStatus('disconnected');
          setMessage('WhatsApp desconectado. Clique em "Conectar" para iniciar.');
        }
      } catch (error) {
        console.error('Erro ao verificar status do WhatsApp:', error);
        setStatus('error');
        setMessage('Erro ao conectar com o servidor WhatsApp.');
      } finally {
        setLoading(false);
      }
    };
    
    checkWhatsAppStatus();
    
    // Simulação de polling para status
    const interval = setInterval(checkWhatsAppStatus, 10000);
    
    return () => clearInterval(interval);
  }, []);
  
  const handleConnect = async () => {
    try {
      setLoading(true);
      setMessage('Iniciando conexão com WhatsApp...');
      
      const data = await fetchWhatsAppStatus();
      
      if (data.qrCode) {
        setStatus('connecting');
        setQrCode(data.qrCode);
        setMessage('Escaneie o código QR para conectar');
      }
    } catch (error) {
      console.error('Erro ao conectar WhatsApp:', error);
      setStatus('error');
      setMessage('Erro ao conectar com o servidor WhatsApp.');
    } finally {
      setLoading(false);
    }
  };
  
  const renderStatusIcon = () => {
    switch (status) {
      case 'connected':
        return <CheckIcon sx={{ color: 'success.main', fontSize: 40 }} />;
      case 'connecting':
        return <QrCodeIcon sx={{ color: 'info.main', fontSize: 40 }} />;
      case 'error':
        return <ErrorIcon sx={{ color: 'error.main', fontSize: 40 }} />;
      default:
        return <PhoneIcon sx={{ color: 'text.secondary', fontSize: 40 }} />;
    }
  };
  
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Conexão com WhatsApp
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Status da Conexão" />
            <Divider />
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                {renderStatusIcon()}
                <Typography variant="h6" sx={{ ml: 2 }}>
                  {status === 'connected' && 'Conectado'}
                  {status === 'connecting' && 'Conectando...'}
                  {status === 'disconnected' && 'Desconectado'}
                  {status === 'error' && 'Erro na Conexão'}
                </Typography>
              </Box>
              
              {message && (
                <Alert 
                  severity={
                    status === 'connected' ? 'success' : 
                    status === 'connecting' ? 'info' : 
                    status === 'error' ? 'error' : 'warning'
                  }
                  sx={{ mb: 3 }}
                >
                  {message}
                </Alert>
              )}
              
              <Button
                variant="contained"
                color="primary"
                startIcon={status === 'disconnected' ? <WhatsAppIcon /> : <RefreshIcon />}
                onClick={handleConnect}
                disabled={loading}
                fullWidth
              >
                {loading ? (
                  <CircularProgress size={24} />
                ) : (
                  status === 'disconnected' ? 'Conectar WhatsApp' : 'Atualizar Conexão'
                )}
              </Button>
            </CardContent>
          </Card>
          
          <Card sx={{ mt: 3 }}>
            <CardHeader title="Instruções" />
            <Divider />
            <CardContent>
              <List>
                <ListItem>
                  <ListItemIcon>
                    <QrCodeIcon />
                  </ListItemIcon>
                  <ListItemText primary="Escaneie o QR Code com seu WhatsApp" secondary="Abra o WhatsApp no seu celular e escaneie o código QR exibido." />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <CheckIcon />
                  </ListItemIcon>
                  <ListItemText primary="Mantenha o telefone conectado" secondary="Certifique-se de que seu telefone esteja conectado à internet e com bateria carregada." />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <RefreshIcon />
                  </ListItemIcon>
                  <ListItemText primary="Atualize se necessário" secondary="Se o QR Code expirar, clique em 'Atualizar Conexão' para gerar um novo." />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Código QR" />
            <Divider />
            <CardContent sx={{ textAlign: 'center', py: 4 }}>
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px' }}>
                  <CircularProgress />
                </Box>
              ) : status === 'connecting' && qrCode ? (
                <Box>
                  <Box 
                    component="img" 
                    src={qrCode} 
                    alt="QR Code para WhatsApp" 
                    sx={{ 
                      maxWidth: '100%', 
                      height: 'auto',
                      border: '8px solid white',
                      boxShadow: 3
                    }} 
                  />
                  <Typography variant="caption" display="block" sx={{ mt: 2, color: 'text.secondary' }}>
                    Escaneie este código com seu WhatsApp
                  </Typography>
                </Box>
              ) : status === 'connected' ? (
                <Box sx={{ p: 4 }}>
                  <CheckIcon sx={{ color: 'success.main', fontSize: 80 }} />
                  <Typography variant="h6" sx={{ mt: 2 }}>
                    WhatsApp conectado com sucesso!
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Você já pode receber e enviar mensagens.
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ p: 4 }}>
                  <WhatsAppIcon sx={{ color: 'text.secondary', fontSize: 80, opacity: 0.5 }} />
                  <Typography variant="h6" sx={{ mt: 2 }}>
                    Não conectado
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Clique em "Conectar WhatsApp" para começar.
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default WhatsappConnection; 