import React, { useEffect, useState } from 'react';
import { db } from '../config/firebase';
import { 
    collection, 
    query, 
    orderBy, 
    onSnapshot,
    getDocs,
    doc,
    getDoc,
    collectionGroup
} from 'firebase/firestore';
import { 
    CheckCircleIcon, 
    ClockIcon, 
    ExclamationCircleIcon,
    ArrowPathIcon
} from '@heroicons/react/24/outline';

interface Message {
    id: string;
    conversationId: string;
    conteudo: string;
    remetente: string;
    timestamp: any;
    tipo: string;
}

interface Conversation {
    id: string;
    cliente: {
        nome: string;
        telefone: string;
    };
    dataHoraInicio: any;
}

const Messages: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState('todas');
    const [conversations, setConversations] = useState<{ [key: string]: Conversation }>({});

    useEffect(() => {
        console.log('Iniciando carregamento de dados...');
        
        try {
            // Usar collectionGroup para buscar todas as mensagens de uma vez
            const mensagensRef = collectionGroup(db, 'mensagens');
            const mensagensQuery = query(mensagensRef, orderBy('timestamp', 'desc'));
            
            const unsubscribe = onSnapshot(mensagensQuery, async (snapshot) => {
                console.log('Mensagens encontradas:', snapshot.size);
                
                const conversationsMap: { [key: string]: Conversation } = {};
                const allMessages: Message[] = [];

                for (const msgDoc of snapshot.docs) {
                    // Extrair o ID da conversa do path da mensagem
                    const pathSegments = msgDoc.ref.path.split('/');
                    const conversationId = pathSegments[1]; // O ID da conversa está no segundo segmento do path

                    // Se ainda não temos os dados desta conversa, vamos buscá-los
                    if (!conversationsMap[conversationId]) {
                        const conversaDoc = await getDoc(doc(db, 'conversas', conversationId));
                        if (conversaDoc.exists()) {
                            const conversaData = conversaDoc.data();
                            conversationsMap[conversationId] = {
                                id: conversationId,
                                cliente: {
                                    nome: conversaData.cliente?.nome || 'Cliente',
                                    telefone: conversaData.cliente?.telefone || conversationId
                                },
                                dataHoraInicio: conversaData.dataHoraInicio
                            };
                        }
                    }

                    const messageData = msgDoc.data();
                    allMessages.push({
                        id: msgDoc.id,
                        conversationId,
                        conteudo: messageData.conteudo || '',
                        remetente: messageData.remetente || 'cliente',
                        timestamp: messageData.timestamp,
                        tipo: messageData.tipo || 'chat'
                    });
                }

                console.log('Total de mensagens encontradas:', allMessages.length);
                setConversations(conversationsMap);
                setMessages(allMessages);
                setLoading(false);
            }, (error) => {
                console.error('Erro ao buscar mensagens:', error);
                setError('Erro ao carregar mensagens');
                setLoading(false);
            });

            return () => {
                console.log('Limpando listeners...');
                unsubscribe();
            };
        } catch (error) {
            console.error('Erro ao configurar listeners:', error);
            setError('Erro ao configurar sistema de mensagens');
            setLoading(false);
        }
    }, []);

    const formatDate = (timestamp: any) => {
        if (!timestamp) return 'N/A';
        try {
            const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
            return new Intl.DateTimeFormat('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }).format(date);
        } catch (error) {
            console.error('Erro ao formatar data:', error);
            return 'Data inválida';
        }
    };

    console.log('Estado atual:', { loading, error, messagesCount: messages.length, conversations });

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <ArrowPathIcon className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center text-red-500 p-4">
                <ExclamationCircleIcon className="h-8 w-8 mx-auto mb-2" />
                <p>{error}</p>
            </div>
        );
    }

    if (messages.length === 0) {
        return (
            <div className="text-center text-gray-500 p-4">
                <p>Nenhuma mensagem encontrada</p>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">Mensagens ({messages.length})</h1>
                <div className="flex gap-2">
                    <button
                        onClick={() => setFilter('todas')}
                        className={`px-4 py-2 rounded ${filter === 'todas' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
                    >
                        Todas
                    </button>
                    <button
                        onClick={() => setFilter('cliente')}
                        className={`px-4 py-2 rounded ${filter === 'cliente' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
                    >
                        Cliente
                    </button>
                    <button
                        onClick={() => setFilter('atendente')}
                        className={`px-4 py-2 rounded ${filter === 'atendente' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
                    >
                        Atendente
                    </button>
                </div>
            </div>

            <div className="overflow-x-auto">
                <table className="min-w-full bg-white rounded-lg overflow-hidden shadow-lg">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cliente</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Mensagem</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Remetente</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data/Hora</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                        {messages
                            .filter(msg => filter === 'todas' || msg.remetente === filter)
                            .map((message) => {
                                const conversation = conversations[message.conversationId];
                                return (
                                    <tr key={message.id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium text-gray-900">
                                                {conversation?.cliente.nome || 'Cliente'}
                                            </div>
                                            <div className="text-sm text-gray-500">
                                                {conversation?.cliente.telefone || message.conversationId}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-sm text-gray-900">{message.conteudo}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                                message.remetente === 'cliente' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                                            }`}>
                                                {message.remetente === 'cliente' ? 'Cliente' : 'Atendente'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {formatDate(message.timestamp)}
                                        </td>
                                    </tr>
                                );
                            })}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default Messages; 