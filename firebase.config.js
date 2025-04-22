const admin = require('firebase-admin');
const dotenv = require('dotenv');
const path = require('path');

// Carrega as variáveis de ambiente
dotenv.config();

// Verifica se já foi inicializado
if (!admin.apps.length) {
    try {
        // Carrega as credenciais do Firebase
        const serviceAccount = require(path.join(__dirname, process.env.FIREBASE_SERVICE_ACCOUNT || 'firebase-credentials.json'));

        // Inicializa o Firebase Admin
        admin.initializeApp({
            credential: admin.credential.cert(serviceAccount),
            storageBucket: process.env.FIREBASE_STORAGE_BUCKET
        });

        console.log('Firebase inicializado com sucesso');
    } catch (error) {
        console.error('Erro ao inicializar Firebase:', error);
        process.exit(1);
    }
}

// Exporta as instâncias do Firebase
module.exports = {
    admin,
    db: admin.firestore(),
    bucket: admin.storage().bucket()
}; 