const admin = require('firebase-admin')
const { Storage } = require('@google-cloud/storage')
const path = require('path')
const fs = require('fs')
const { format } = require('date-fns')

// Inicializa o Firebase Admin
const serviceAccount = require('../service-account.json')
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
})

const db = admin.firestore()
const storage = new Storage({
  projectId: serviceAccount.project_id,
  credentials: serviceAccount
})

const BUCKET_NAME = 'seu-bucket-de-backup'
const BACKUP_DIR = path.join(__dirname, '../backups')

// Cria o diretório de backup se não existir
if (!fs.existsSync(BACKUP_DIR)) {
  fs.mkdirSync(BACKUP_DIR, { recursive: true })
}

async function backupCollection(collectionName) {
  console.log(`Iniciando backup da coleção ${collectionName}...`)
  
  const snapshot = await db.collection(collectionName).get()
  const data = []
  
  snapshot.forEach(doc => {
    data.push({
      id: doc.id,
      ...doc.data()
    })
  })
  
  const timestamp = format(new Date(), 'yyyy-MM-dd_HH-mm-ss')
  const filename = `${collectionName}_${timestamp}.json`
  const filepath = path.join(BACKUP_DIR, filename)
  
  fs.writeFileSync(filepath, JSON.stringify(data, null, 2))
  console.log(`Backup da coleção ${collectionName} salvo em ${filepath}`)
  
  // Upload para o Google Cloud Storage
  await storage.bucket(BUCKET_NAME).upload(filepath, {
    destination: `backups/${filename}`
  })
  console.log(`Backup da coleção ${collectionName} enviado para o Google Cloud Storage`)
  
  // Remove o arquivo local
  fs.unlinkSync(filepath)
}

async function backupAllCollections() {
  const collections = [
    'conversations',
    'evaluations',
    'attendances',
    'requests'
  ]
  
  for (const collection of collections) {
    try {
      await backupCollection(collection)
    } catch (error) {
      console.error(`Erro ao fazer backup da coleção ${collection}:`, error)
    }
  }
}

// Executa o backup
backupAllCollections()
  .then(() => {
    console.log('Backup concluído com sucesso!')
    process.exit(0)
  })
  .catch(error => {
    console.error('Erro durante o backup:', error)
    process.exit(1)
  }) 