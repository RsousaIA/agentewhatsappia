import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  WhatsApp as WhatsAppIcon,
  Message as MessageIcon,
  QuestionAnswer as ConversationIcon,
  CheckCircle as ClosedIcon,
  Assessment as EvaluationIcon,
  Warning as CriticalIcon,
  Inbox as AllMessagesIcon,
  Person as ProfileIcon,
  Logout as LogoutIcon
} from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';

const drawerWidth = 260;

const menuItems = [
  {
    title: 'Dashboard',
    icon: <DashboardIcon />,
    path: '/dashboard'
  },
  {
    title: 'Conexão WhatsApp',
    icon: <WhatsAppIcon />,
    path: '/whatsapp-connection'
  },
  {
    title: 'Todas as Mensagens',
    icon: <AllMessagesIcon />,
    path: '/all-messages'
  },
  {
    title: 'Conversas em Andamento',
    icon: <ConversationIcon />,
    path: '/active-conversations'
  },
  {
    title: 'Conversas Fechadas',
    icon: <ClosedIcon />,
    path: '/closed-conversations'
  },
  {
    title: 'Conversas Avaliadas',
    icon: <EvaluationIcon />,
    path: '/evaluated-conversations'
  },
  {
    title: 'Atendimentos Críticos',
    icon: <CriticalIcon />,
    path: '/critical-conversations'
  },
];

const Sidebar = ({ open, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout, currentUser } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Erro ao fazer logout:', error);
    }
  };

  return (
    <Drawer
      variant="permanent"
      open={true}
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
        },
      }}
    >
      <Box sx={{ 
        height: '64px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        bgcolor: 'primary.main',
        color: 'white'
      }}>
        <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
          Suporte WhatsApp
        </Typography>
      </Box>
      
      <Divider />
      
      <Box sx={{ px: 2, py: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Olá, {currentUser?.email || 'Usuário'}
        </Typography>
      </Box>
      
      <Divider />
      
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => navigate(item.path)}
            >
              <ListItemIcon>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.title} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      
      <Divider />
      
      <List>
        <ListItem disablePadding>
          <ListItemButton onClick={() => navigate('/profile')}>
            <ListItemIcon>
              <ProfileIcon />
            </ListItemIcon>
            <ListItemText primary="Meu Perfil" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton onClick={handleLogout}>
            <ListItemIcon>
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText primary="Sair" />
          </ListItemButton>
        </ListItem>
      </List>
    </Drawer>
  );
};

export default Sidebar; 