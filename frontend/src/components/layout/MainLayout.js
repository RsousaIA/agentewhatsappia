import React from 'react';
import { Box, CssBaseline } from '@mui/material';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

const MainLayout = ({ children }) => {
  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      <CssBaseline />
      
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main Content */}
      <Box component="main" sx={{ flexGrow: 1, p: 0, display: 'flex', flexDirection: 'column' }}>
        <TopBar />
        <Box sx={{ p: 3, overflowY: 'auto', flexGrow: 1 }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
};

export default MainLayout; 