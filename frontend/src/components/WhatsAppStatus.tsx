import React, { useState, useEffect } from 'react';

interface WhatsAppStatusProps {
  className?: string;
}

const WhatsAppStatus: React.FC<WhatsAppStatusProps> = ({ className = '' }) => {
  const [status, setStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const [lastMessage, setLastMessage] = useState<string>('');
  const [lastMessageTime, setLastMessageTime] = useState<string>('');

  useEffect(() => {
    // Aqui você poderia implementar a lógica real para verificar o status do WhatsApp
    // Por enquanto, vamos simular um status
    const checkStatus = () => {
      // Simulação: 50% de chance de estar conectado
      setStatus(Math.random() > 0.5 ? 'connected' : 'disconnected');
      
      if (Math.random() > 0.5) {
        setLastMessage('Olá! Como posso ajudar?');
        setLastMessageTime(new Date().toLocaleTimeString());
      }
    };
    
    checkStatus();
    
    // Verificar periodicamente
    const interval = setInterval(checkStatus, 30000);
    
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <h2 className="text-lg font-semibold mb-4">Status do WhatsApp</h2>
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <div className={`w-3 h-3 rounded-full ${status === 'connected' ? 'bg-green-500' : 'bg-red-500'} mr-2`} />
          <span className="text-sm font-medium text-gray-700">
            {status === 'connected' ? 'Conectado' : 'Desconectado'}
          </span>
        </div>
        {lastMessageTime && (
          <div className="text-sm text-gray-500">
            Última mensagem: {lastMessageTime}
          </div>
        )}
      </div>
      {lastMessage && (
        <div className="mt-4">
          <p className="text-sm text-gray-600">Última mensagem:</p>
          <p className="text-sm font-medium text-gray-900 mt-1">{lastMessage}</p>
        </div>
      )}
    </div>
  );
};

export default WhatsAppStatus; 