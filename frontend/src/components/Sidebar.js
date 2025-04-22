import React from 'react';
import { 
  Drawer, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText, 
  Divider, 
  Box, 
  Typography, 
  Button,
  Avatar,
  useTheme,
  styled
} from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';

// Ícones
import DashboardIcon from '@mui/icons-material/Dashboard';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import EmailIcon from '@mui/icons-material/Email';
import ChatIcon from '@mui/icons-material/Chat';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import StarIcon from '@mui/icons-material/Star';
import WarningIcon from '@mui/icons-material/Warning';
import LogoutIcon from '@mui/icons-material/Logout';

import { auth } from '../services/firebase';
import { signOut } from 'firebase/auth';

// Largura da barra lateral
const drawerWidth = 280;

// Componentes estilizados
const StyledDrawer = styled(Drawer)(() => ({
  width: drawerWidth,
  flexShrink: 0,
  '& .MuiDrawer-paper': {
    width: drawerWidth,
    boxSizing: 'border-box',
    backgroundColor: '#1a237e',
    color: '#fff',
    borderRight: 'none',
  },
}));

const StyledListItem = styled(ListItem)(({ theme, selected }) => ({
  margin: theme.spacing(0.8, 1),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: selected ? 'rgba(255, 255, 255, 0.2)' : 'transparent',
  '&:hover': {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
}));

const StyledListItemText = styled(ListItemText)(() => ({
  '& .MuiListItemText-primary': {
    fontWeight: 500,
    fontSize: '0.95rem',
  },
}));

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  
  // Opções de menu da barra lateral
  const menuItems = [
    { path: '/dashboard', text: 'Dashboard', icon: <DashboardIcon /> },
    { path: '/whatsapp', text: 'Conexão WhatsApp', icon: <WhatsAppIcon /> },
    { path: '/mensagens', text: 'Mensagens Recebidas', icon: <EmailIcon /> },
    { path: '/conversas-andamento', text: 'Conversas em Andamento', icon: <ChatIcon /> },
    { path: '/conversas-fechadas', text: 'Conversas Fechadas', icon: <CheckCircleIcon /> },
    { path: '/conversas-avaliadas', text: 'Conversas Avaliadas', icon: <StarIcon /> },
    { path: '/atendimentos-criticos', text: 'Atendimentos Críticos', icon: <WarningIcon /> },
  ];

  // Verificar se um item está selecionado
  const isSelected = (path) => {
    return location.pathname === path;
  };

  // Manipular logout
  const handleLogout = async () => {
    try {
      await signOut(auth);
      // Redirecionamento é tratado pelo componente de rotas protegidas
    } catch (error) {
      console.error('Erro ao fazer logout:', error);
    }
  };

  // Navegar para outras páginas
  const navigateTo = (path) => {
    navigate(path);
  };

  return (
    <StyledDrawer variant="permanent" anchor="left">
      {/* Cabeçalho/Logo */}
      <Box
        sx={{
          padding: theme.spacing(3),
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        <Avatar
          src="/logo.png"
          alt="Logo"
          sx={{
            width: 60,
            height: 60,
            backgroundColor: 'white',
            mb: 2,
          }}
        >
          <WhatsAppIcon fontSize="large" sx={{ color: '#1a237e' }} />
        </Avatar>
        <Typography variant="h6" component="div" align="center" sx={{ fontWeight: 600 }}>
          Suporte WhatsApp
        </Typography>
        <Typography variant="body2" align="center" sx={{ opacity: 0.8, mt: 0.5 }}>
          Sistema de Atendimento
        </Typography>
      </Box>

      {/* Menu de navegação */}
      <List sx={{ mt: 2, px: 1 }}>
        {menuItems.map((item) => (
          <StyledListItem
            key={item.path}
            button
            selected={isSelected(item.path)}
            onClick={() => navigateTo(item.path)}
          >
            <ListItemIcon sx={{ color: 'white', minWidth: 40 }}>
              {item.icon}
            </ListItemIcon>
            <StyledListItemText primary={item.text} />
          </StyledListItem>
        ))}
      </List>

      <Box sx={{ flexGrow: 1 }} />

      {/* Botão de logout */}
      <Box sx={{ p: 2, borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <Button
          variant="outlined"
          color="inherit"
          startIcon={<LogoutIcon />}
          onClick={handleLogout}
          fullWidth
          sx={{
            borderColor: 'rgba(255, 255, 255, 0.3)',
            '&:hover': {
              borderColor: 'rgba(255, 255, 255, 0.8)',
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
            },
            textTransform: 'none',
            justifyContent: 'flex-start',
            py: 1,
          }}
        >
          Sair
        </Button>
      </Box>
    </StyledDrawer>
  );
};

export default Sidebar; 