import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { auth } from './services/firebase';
import { onAuthStateChanged } from 'firebase/auth';

// Páginas
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import WhatsAppConnectionPage from './pages/WhatsAppConnectionPage';
import MessagesPage from './pages/MessagesPage';
import ActiveConversationsPage from './pages/ActiveConversationsPage';
import ClosedConversationsPage from './pages/ClosedConversationsPage';
import EvaluatedConversationsPage from './pages/EvaluatedConversationsPage';
import CriticalAttendancesPage from './pages/CriticalAttendancesPage';
import NotFoundPage from './pages/NotFoundPage';

// Componentes
import Sidebar from './components/Sidebar';
import Header from './components/Header';

// Rota de autenticação
const AuthRoute = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = React.useState(false);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setIsAuthenticated(!!user);
      setLoading(false);
    });
    
    return () => unsubscribe();
  }, []);

  if (loading) {
    return <div>Carregando...</div>;
  }

  return isAuthenticated ? children : <Navigate to="/login" />;
};

// Tema
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#4791db',
      dark: '#115293',
    },
    secondary: {
      main: '#dc004e',
      light: '#e33371',
      dark: '#9a0036',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 500,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 500,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 500,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 500,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 500,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 500,
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          {/* Rotas públicas */}
          <Route path="/login" element={<LoginPage />} />
          
          {/* Rotas protegidas */}
          <Route
            path="/"
            element={
              <AuthRoute>
                <div style={{ display: 'flex' }}>
                  <Sidebar />
                  <div style={{ flexGrow: 1 }}>
                    <Header />
                    <main style={{ padding: '20px' }}>
                      <DashboardPage />
                    </main>
                  </div>
                </div>
              </AuthRoute>
            }
          />
          <Route
            path="/whatsapp-connection"
            element={
              <AuthRoute>
                <div style={{ display: 'flex' }}>
                  <Sidebar />
                  <div style={{ flexGrow: 1 }}>
                    <Header />
                    <main style={{ padding: '20px' }}>
                      <WhatsAppConnectionPage />
                    </main>
                  </div>
                </div>
              </AuthRoute>
            }
          />
          <Route
            path="/messages"
            element={
              <AuthRoute>
                <div style={{ display: 'flex' }}>
                  <Sidebar />
                  <div style={{ flexGrow: 1 }}>
                    <Header />
                    <main style={{ padding: '20px' }}>
                      <MessagesPage />
                    </main>
                  </div>
                </div>
              </AuthRoute>
            }
          />
          <Route
            path="/active-conversations"
            element={
              <AuthRoute>
                <div style={{ display: 'flex' }}>
                  <Sidebar />
                  <div style={{ flexGrow: 1 }}>
                    <Header />
                    <main style={{ padding: '20px' }}>
                      <ActiveConversationsPage />
                    </main>
                  </div>
                </div>
              </AuthRoute>
            }
          />
          <Route
            path="/closed-conversations"
            element={
              <AuthRoute>
                <div style={{ display: 'flex' }}>
                  <Sidebar />
                  <div style={{ flexGrow: 1 }}>
                    <Header />
                    <main style={{ padding: '20px' }}>
                      <ClosedConversationsPage />
                    </main>
                  </div>
                </div>
              </AuthRoute>
            }
          />
          <Route
            path="/evaluated-conversations"
            element={
              <AuthRoute>
                <div style={{ display: 'flex' }}>
                  <Sidebar />
                  <div style={{ flexGrow: 1 }}>
                    <Header />
                    <main style={{ padding: '20px' }}>
                      <EvaluatedConversationsPage />
                    </main>
                  </div>
                </div>
              </AuthRoute>
            }
          />
          <Route
            path="/critical-attendances"
            element={
              <AuthRoute>
                <div style={{ display: 'flex' }}>
                  <Sidebar />
                  <div style={{ flexGrow: 1 }}>
                    <Header />
                    <main style={{ padding: '20px' }}>
                      <CriticalAttendancesPage />
                    </main>
                  </div>
                </div>
              </AuthRoute>
            }
          />
          
          {/* Página não encontrada */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App; 