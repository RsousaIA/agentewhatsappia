const { initializeApp, cert } = require('firebase-admin/app');
const { getFirestore } = require('firebase-admin/firestore');
const { getStorage } = require('firebase-admin/storage');
const log = require('./logger');
const dotenv = require('dotenv');

// Carrega variáveis de ambiente
dotenv.config();

async function testFirebase() {
    log.info('Iniciando teste do Firebase...');

    try {
        // Inicializa o Firebase
        const app = initializeApp({
            credential: cert({
                projectId: process.env.FIREBASE_PROJECT_ID,
                clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
                privateKey: process.env.FIREBASE_PRIVATE_KEY.replace(/\\n/g, '\n')
            }),
            storageBucket: process.env.FIREBASE_STORAGE_BUCKET
        });

        const db = getFirestore(app);
        const bucket = getStorage(app).bucket();

        log.firebase('Firebase inicializado com sucesso');

        // Testa Firestore
        const testDoc = {
            test: 'teste',
            timestamp: new Date().toISOString()
        };

        const docRef = await db.collection('test').add(testDoc);
        log.firebase('Documento criado no Firestore', { docId: docRef.id });

        // Testa Storage
        const testFile = Buffer.from('teste de arquivo');
        const file = bucket.file('test/test.txt');
        await file.save(testFile, {
            metadata: {
                contentType: 'text/plain'
            }
        });
        log.firebase('Arquivo criado no Storage', { path: 'test/test.txt' });

        // Limpa os testes
        await docRef.delete();
        await file.delete();
        log.firebase('Testes limpos com sucesso');

        console.log('✅ Teste do Firebase concluído com sucesso!');
    } catch (error) {
        log.error('Erro durante teste do Firebase', {
            error: error.message,
            stack: error.stack
        });
        console.error('❌ Erro durante teste do Firebase:', error.message);
        process.exit(1);
    }
}

// Executa o teste
testFirebase(); 