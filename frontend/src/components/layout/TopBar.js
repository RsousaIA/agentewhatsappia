import React from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  IconButton,
  Box,
  Avatar,
  Badge,
  Tooltip,
  useTheme
} from '@mui/material';
import { 
  Notifications as NotificationsIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon
} from '@mui/icons-material';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

// Função para obter o título da página com base na rota atual
const getPageTitle = (pathname) => {
  const pathMap = {
    '/dashboard': 'Dashboard',
    '/whatsapp-connection': 'Conexão WhatsApp',
    '/all-messages': 'Todas as Mensagens',
    '/active-conversations': 'Conversas em Andamento',
    '/closed-conversations': 'Conversas Encerradas',
    '/evaluated-conversations': 'Conversas Avaliadas',
    '/critical-conversations': 'Atendimentos Críticos',
    '/profile': 'Meu Perfil'
  };
  
  return pathMap[pathname] || 'Suporte WhatsApp';
};

const TopBar = () => {
  const theme = useTheme();
  const location = useLocation();
  const { currentUser } = useAuth();
  
  // Pegar as iniciais do email para o avatar
  const getInitials = (email) => {
    if (!email) return 'U';
    return email.charAt(0).toUpperCase();
  };
  
  return (
    <AppBar 
      position="static" 
      color="default" 
      elevation={0}
      sx={{ 
        borderBottom: `1px solid ${theme.palette.divider}`,
        backgroundColor: 'background.paper'
      }}
    >
      <Toolbar>
        <Typography
          variant="h6"
          color="inherit"
          noWrap
          sx={{ flexGrow: 1 }}
        >
          {getPageTitle(location.pathname)}
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Tooltip title="Atualizar dados">
            <IconButton size="large" color="inherit">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Notificações">
            <IconButton size="large" color="inherit">
              <Badge badgeContent={4} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Configurações">
            <IconButton size="large" color="inherit">
              <SettingsIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title={currentUser?.email || 'Usuário'}>
            <Avatar 
              sx={{ 
                width: 32, 
                height: 32, 
                marginLeft: 1,
                bgcolor: 'primary.main'
              }}
            >
              {getInitials(currentUser?.email)}
            </Avatar>
          </Tooltip>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default TopBar; 