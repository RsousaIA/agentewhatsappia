import React, { useState, useEffect } from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  IconButton, 
  Badge, 
  Avatar, 
  Menu, 
  MenuItem, 
  Box,
  ListItemIcon,
  ListItemText,
  Divider,
  Tooltip
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { auth, db } from '../services/firebase';
import { doc, getDoc } from 'firebase/auth';
import { signOut } from 'firebase/auth';

// Ícones
import NotificationsIcon from '@mui/icons-material/Notifications';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import LogoutIcon from '@mui/icons-material/Logout';
import SettingsIcon from '@mui/icons-material/Settings';
import PersonIcon from '@mui/icons-material/Person';

// Largura da barra lateral para compensar no posicionamento
const drawerWidth = 280;

const StyledAppBar = styled(AppBar)(({ theme }) => ({
  width: `calc(100% - ${drawerWidth}px)`,
  marginLeft: drawerWidth,
  backgroundColor: '#fff',
  color: '#333',
  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24)',
}));

const Header = ({ title }) => {
  const [userName, setUserName] = useState('');
  const [notifications, setNotifications] = useState([]);
  const [notificationCount, setNotificationCount] = useState(0);
  const [anchorElNotifications, setAnchorElNotifications] = useState(null);
  const [anchorElProfile, setAnchorElProfile] = useState(null);

  useEffect(() => {
    // Buscar nome do usuário logado
    const fetchUserName = async () => {
      try {
        const user = auth.currentUser;
        if (user) {
          // Se precisar buscar mais dados do usuário do Firestore
          // const userDoc = await getDoc(doc(db, "usuarios", user.uid));
          // const userData = userDoc.data();
          // setUserName(userData?.nome || user.displayName || 'Usuário');
          setUserName(user.displayName || user.email || 'Usuário');
        }
      } catch (error) {
        console.error('Erro ao buscar nome do usuário:', error);
      }
    };

    fetchUserName();

    // Simulação de notificações - em produção, use listeners do Firestore
    setNotifications([
      {
        id: 1,
        message: 'Nova mensagem recebida',
        time: '5 min atrás',
        read: false
      },
      {
        id: 2,
        message: 'Conversa em espera por 15 minutos',
        time: '15 min atrás',
        read: false
      },
      {
        id: 3,
        message: 'Atendimento avaliado como crítico',
        time: '1 hora atrás',
        read: true
      }
    ]);
    setNotificationCount(2); // Notificações não lidas
  }, []);

  // Manipuladores de eventos para menus
  const handleNotificationClick = (event) => {
    setAnchorElNotifications(event.currentTarget);
  };

  const handleNotificationClose = () => {
    setAnchorElNotifications(null);
  };

  const handleProfileClick = (event) => {
    setAnchorElProfile(event.currentTarget);
  };

  const handleProfileClose = () => {
    setAnchorElProfile(null);
  };

  const handleLogout = async () => {
    try {
      await signOut(auth);
      // Redirecionamento é tratado no componente de rotas protegidas
    } catch (error) {
      console.error('Erro ao fazer logout:', error);
    }
    handleProfileClose();
  };

  return (
    <StyledAppBar position="fixed">
      <Toolbar>
        <Typography 
          variant="h6" 
          component="div" 
          sx={{ 
            flexGrow: 1, 
            fontWeight: 600,
            ml: 1
          }}
        >
          {title || 'Dashboard'}
        </Typography>

        {/* Botão de Notificações */}
        <Tooltip title="Notificações">
          <IconButton 
            size="large" 
            color="inherit" 
            onClick={handleNotificationClick}
          >
            <Badge badgeContent={notificationCount} color="error">
              <NotificationsIcon />
            </Badge>
          </IconButton>
        </Tooltip>

        {/* Menu de Notificações */}
        <Menu
          anchorEl={anchorElNotifications}
          open={Boolean(anchorElNotifications)}
          onClose={handleNotificationClose}
          PaperProps={{
            elevation: 3,
            sx: { 
              width: 320,
              maxHeight: 360,
              mt: 1.5,
              borderRadius: 1
            },
          }}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        >
          <Typography sx={{ p: 2, fontWeight: 600 }}>
            Notificações
          </Typography>
          
          <Divider />
          
          {notifications.length === 0 ? (
            <Box sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                Nenhuma notificação
              </Typography>
            </Box>
          ) : (
            notifications.map((notification) => (
              <MenuItem 
                key={notification.id} 
                onClick={handleNotificationClose}
                sx={{ 
                  py: 1.5,
                  px: 2,
                  borderLeft: notification.read ? 'none' : '3px solid #1a237e',
                  backgroundColor: notification.read ? 'inherit' : 'rgba(26, 35, 126, 0.05)',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.04)'
                  }
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                  <Typography variant="body1">
                    {notification.message}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {notification.time}
                  </Typography>
                </Box>
              </MenuItem>
            ))
          )}
          
          {notifications.length > 0 && (
            <>
              <Divider />
              <Box sx={{ p: 1, textAlign: 'center' }}>
                <Typography 
                  variant="body2" 
                  color="primary" 
                  sx={{ cursor: 'pointer', py: 0.5 }}
                  onClick={handleNotificationClose}
                >
                  Ver todas as notificações
                </Typography>
              </Box>
            </>
          )}
        </Menu>

        {/* Perfil do Usuário */}
        <Box sx={{ display: 'flex', alignItems: 'center', ml: 1 }}>
          <Typography variant="body2" sx={{ mr: 2, display: { xs: 'none', md: 'block' } }}>
            {userName}
          </Typography>
          
          <Tooltip title="Conta">
            <IconButton
              onClick={handleProfileClick}
              size="small"
              edge="end"
              aria-haspopup="true"
            >
              <Avatar sx={{ bgcolor: '#1a237e', width: 35, height: 35 }}>
                {userName.charAt(0).toUpperCase()}
              </Avatar>
            </IconButton>
          </Tooltip>
        </Box>

        {/* Menu de Perfil */}
        <Menu
          anchorEl={anchorElProfile}
          open={Boolean(anchorElProfile)}
          onClose={handleProfileClose}
          PaperProps={{
            elevation: 3,
            sx: { 
              width: 220,
              mt: 1.5,
              borderRadius: 1
            },
          }}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        >
          <Box sx={{ pt: 2, pb: 1, px: 2, textAlign: 'center' }}>
            <Avatar sx={{ bgcolor: '#1a237e', width: 40, height: 40, mx: 'auto' }}>
              {userName.charAt(0).toUpperCase()}
            </Avatar>
            <Typography variant="body1" sx={{ mt: 1, fontWeight: 500 }}>
              {userName}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Atendente
            </Typography>
          </Box>
          
          <Divider />
          
          <MenuItem onClick={handleProfileClose}>
            <ListItemIcon>
              <PersonIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Meu perfil</ListItemText>
          </MenuItem>
          
          <MenuItem onClick={handleProfileClose}>
            <ListItemIcon>
              <SettingsIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Configurações</ListItemText>
          </MenuItem>
          
          <Divider />
          
          <MenuItem onClick={handleLogout}>
            <ListItemIcon>
              <LogoutIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Sair</ListItemText>
          </MenuItem>
        </Menu>
      </Toolbar>
    </StyledAppBar>
  );
};

export default Header; 