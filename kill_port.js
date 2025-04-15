const { exec } = require('child_process');

// Comando para Windows
const command = 'netstat -ano | findstr :3000';

exec(command, (error, stdout, stderr) => {
    if (error) {
        console.error(`Erro ao executar comando: ${error}`);
        return;
    }

    if (stdout) {
        const lines = stdout.split('\n');
        lines.forEach(line => {
            if (line.trim()) {
                const parts = line.trim().split(/\s+/);
                const pid = parts[parts.length - 1];
                console.log(`Matando processo com PID: ${pid}`);
                exec(`taskkill /F /PID ${pid}`, (err) => {
                    if (err) {
                        console.error(`Erro ao matar processo ${pid}: ${err}`);
                    } else {
                        console.log(`Processo ${pid} morto com sucesso`);
                    }
                });
            }
        });
    } else {
        console.log('Nenhum processo encontrado na porta 3000');
    }
}); 