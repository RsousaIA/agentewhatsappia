import { io, Socket } from 'socket.io-client';
import axios from 'axios';

const WHATSAPP_SERVER_URL = import.meta.env.VITE_WHATSAPP_SERVER_URL || 'http://localhost:5000';
const API_URL = `${WHATSAPP_SERVER_URL}/api`;

interface WhatsAppStatus {
  status: 'disconnected' | 'qr_ready' | 'connected';
  qr: string | null;
  lastError: string | null;
}

interface Message {
  id: string;
  conversationId: string;
  from: string;
  fromName: string;
  body: string;
  timestamp: Date;
  type: string;
  direction: 'sent' | 'received';
  isRead: boolean;
}

interface Conversation {
  id: string;
  client: {
    id: string;
    name: string;
    phone: string;
  };
  status: string;
  lastMessageBody: string;
  lastMessageAt: Date;
  unreadCount: number;
}

class WhatsAppService {
  private socket: Socket | null = null;
  private statusListeners: ((status: WhatsAppStatus) => void)[] = [];
  private messageListeners: ((message: Message) => void)[] = [];
  private qrListeners: ((qrCode: string) => void)[] = [];
  
  constructor() {
    this.initializeSocket();
  }
  
  private initializeSocket() {
    try {
      this.socket = io(WHATSAPP_SERVER_URL);
      
      this.socket.on('connect', () => {
        console.log('Conectado ao servidor WhatsApp');
      });
      
      this.socket.on('disconnect', () => {
        console.log('Desconectado do servidor WhatsApp');
      });
      
      this.socket.on('qr', (qrCode: string) => {
        this.qrListeners.forEach(listener => listener(qrCode));
      });
      
      this.socket.on('ready', () => {
        this.getStatus().then(status => {
          this.statusListeners.forEach(listener => listener(status));
        });
      });
      
      this.socket.on('disconnected', () => {
        this.getStatus().then(status => {
          this.statusListeners.forEach(listener => listener(status));
        });
      });
      
      this.socket.on('message', (message: Message) => {
        this.messageListeners.forEach(listener => listener(message));
      });
    } catch (error) {
      console.error('Erro ao inicializar socket:', error);
    }
  }
  
  public async getStatus(): Promise<WhatsAppStatus> {
    try {
      const response = await axios.get<WhatsAppStatus>(`${WHATSAPP_SERVER_URL}/status`);
      return response.data;
    } catch (error) {
      console.error('Erro ao obter status do WhatsApp:', error);
      return {
        status: 'disconnected',
        qr: null,
        lastError: 'Erro ao conectar ao servidor'
      };
    }
  }
  
  public async getConversations(): Promise<Conversation[]> {
    try {
      const response = await axios.get<Conversation[]>(`${API_URL}/conversations`);
      return response.data;
    } catch (error) {
      console.error('Erro ao obter conversas:', error);
      return [];
    }
  }
  
  public async getMessages(conversationId: string): Promise<Message[]> {
    try {
      const phoneNumber = conversationId.replace('@c.us', '');
      const response = await axios.get<Message[]>(`${API_URL}/messages/${phoneNumber}`);
      return response.data;
    } catch (error) {
      console.error('Erro ao obter mensagens:', error);
      return [];
    }
  }
  
  public async sendMessage(to: string, message: string): Promise<boolean> {
    try {
      const response = await axios.post(`${API_URL}/send-message`, { to, message });
      return response.data.status;
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
      return false;
    }
  }
  
  public onStatus(callback: (status: WhatsAppStatus) => void): () => void {
    this.statusListeners.push(callback);
    return () => {
      this.statusListeners = this.statusListeners.filter(listener => listener !== callback);
    };
  }
  
  public onMessage(callback: (message: Message) => void): () => void {
    this.messageListeners.push(callback);
    return () => {
      this.messageListeners = this.messageListeners.filter(listener => listener !== callback);
    };
  }
  
  public onQR(callback: (qrCode: string) => void): () => void {
    this.qrListeners.push(callback);
    return () => {
      this.qrListeners = this.qrListeners.filter(listener => listener !== callback);
    };
  }
  
  public disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
}

// Singleton para uso em toda a aplicação
const whatsappService = new WhatsAppService();
export default whatsappService; 