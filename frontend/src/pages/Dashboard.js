import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Grid, 
  Paper, 
  Typography, 
  Divider,
  Card, 
  CardContent,
  CardHeader,
  Button,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar
} from '@mui/material';
import { 
  Message as MessageIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Chat as ChatIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import { 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

import { getDashboardData, listenToActiveConversations } from '../services/firebase';

// Cores para gráficos
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [activeConversations, setActiveConversations] = useState([]);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        const dashData = await getDashboardData();
        setStats(dashData);
        setLoading(false);
      } catch (error) {
        console.error('Erro ao buscar dados do dashboard:', error);
        setLoading(false);
      }
    };
    
    fetchData();
    
    // Configurar listener para conversas ativas em tempo real
    const unsubscribe = listenToActiveConversations((conversations) => {
      setActiveConversations(conversations);
    });
    
    return () => {
      unsubscribe();
    };
  }, []);
  
  // Dados para o gráfico de pizza
  const statusData = [
    { name: 'Ativas', value: stats?.totalActive || 0, color: '#0088FE' },
    { name: 'Encerradas', value: stats?.totalClosed || 0, color: '#00C49F' }
  ];
  
  // Dados simulados para o gráfico de barras (métricas de avaliação)
  const evaluationData = [
    { name: 'Comunicação', score: 8.5 },
    { name: 'Conhecimento', score: 7.8 },
    { name: 'Empatia', score: 9.2 },
    { name: 'Profissionalismo', score: 8.9 },
    { name: 'Resultados', score: 7.5 },
  ];
  
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }
  
  return (
    <Box>
      <Grid container spacing={3}>
        {/* Cards de estatísticas */}
        <Grid item xs={12} md={3}>
          <Paper 
            elevation={2} 
            sx={{ 
              p: 2, 
              display: 'flex', 
              alignItems: 'center',
              backgroundColor: '#e3f2fd'
            }}
          >
            <Avatar sx={{ bgcolor: '#1976d2', mr: 2 }}>
              <ChatIcon />
            </Avatar>
            <Box>
              <Typography variant="h5" component="div">
                {stats?.totalConversations || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total de Conversas
              </Typography>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Paper 
            elevation={2} 
            sx={{ 
              p: 2, 
              display: 'flex', 
              alignItems: 'center',
              backgroundColor: '#e8f5e9'
            }}
          >
            <Avatar sx={{ bgcolor: '#2e7d32', mr: 2 }}>
              <MessageIcon />
            </Avatar>
            <Box>
              <Typography variant="h5" component="div">
                {stats?.totalActive || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Conversas Ativas
              </Typography>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Paper 
            elevation={2} 
            sx={{ 
              p: 2, 
              display: 'flex', 
              alignItems: 'center',
              backgroundColor: '#fff8e1'
            }}
          >
            <Avatar sx={{ bgcolor: '#ff9800', mr: 2 }}>
              <CheckIcon />
            </Avatar>
            <Box>
              <Typography variant="h5" component="div">
                {stats?.totalClosed || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Conversas Encerradas
              </Typography>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Paper 
            elevation={2} 
            sx={{ 
              p: 2, 
              display: 'flex', 
              alignItems: 'center',
              backgroundColor: '#ffebee'
            }}
          >
            <Avatar sx={{ bgcolor: '#d32f2f', mr: 2 }}>
              <WarningIcon />
            </Avatar>
            <Box>
              <Typography variant="h5" component="div">
                0
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Atendimentos Críticos
              </Typography>
            </Box>
          </Paper>
        </Grid>
        
        {/* Gráficos */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Status das Conversas" />
            <Divider />
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={statusData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {statusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Métricas de Avaliação" />
            <Divider />
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={evaluationData}
                  margin={{
                    top: 5,
                    right: 30,
                    left: 20,
                    bottom: 5,
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={[0, 10]} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="score" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Conversas ativas */}
        <Grid item xs={12}>
          <Card>
            <CardHeader 
              title="Conversas Ativas" 
              action={
                <Button color="primary" variant="text">
                  Ver Todas
                </Button>
              }
            />
            <Divider />
            <CardContent>
              {activeConversations.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 3 }}>
                  Nenhuma conversa ativa no momento
                </Typography>
              ) : (
                <List>
                  {activeConversations.slice(0, 5).map((conversation) => (
                    <ListItem key={conversation.id} divider>
                      <ListItemAvatar>
                        <Avatar>
                          <ChatIcon />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={conversation.cliente?.nome || conversation.cliente?.telefone || 'Cliente'}
                        secondary={`Última atividade: ${formatDistanceToNow(
                          new Date(conversation.ultimaMensagem.toDate ? conversation.ultimaMensagem.toDate() : conversation.ultimaMensagem),
                          { addSuffix: true, locale: ptBR }
                        )}`}
                      />
                      <Button size="small" variant="outlined">
                        Ver Detalhes
                      </Button>
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard; 