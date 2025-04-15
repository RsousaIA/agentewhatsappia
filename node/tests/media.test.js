const fs = require('fs');
const path = require('path');
const { MEDIA_TYPES, processMedia, generateUniqueFilename } = require('../utils/media');

describe('Media Utils', () => {
    describe('MEDIA_TYPES', () => {
        it('should have all required media types', () => {
            expect(MEDIA_TYPES).toHaveProperty('IMAGE');
            expect(MEDIA_TYPES).toHaveProperty('DOCUMENT');
            expect(MEDIA_TYPES).toHaveProperty('AUDIO');
            expect(MEDIA_TYPES).toHaveProperty('VIDEO');
            expect(MEDIA_TYPES).toHaveProperty('STICKER');
        });
    });

    describe('generateUniqueFilename', () => {
        it('should generate unique filenames', () => {
            const originalName = 'test.jpg';
            const filename1 = generateUniqueFilename(originalName);
            const filename2 = generateUniqueFilename(originalName);

            expect(filename1).not.toBe(filename2);
            expect(filename1).toMatch(/^\d+-[a-z0-9]+\.jpg$/);
            expect(filename2).toMatch(/^\d+-[a-z0-9]+\.jpg$/);
        });

        it('should preserve file extensions', () => {
            const filenames = [
                'test.jpg',
                'document.pdf',
                'audio.mp3',
                'video.mp4',
                'sticker.webp'
            ];

            filenames.forEach(originalName => {
                const ext = path.extname(originalName);
                const filename = generateUniqueFilename(originalName);
                expect(filename).toEndWith(ext);
            });
        });
    });

    describe('processMedia', () => {
        const tempDir = path.join(__dirname, '../temp');
        const testFile = path.join(tempDir, 'test.jpg');

        beforeEach(() => {
            // Cria diretório temporário se não existir
            if (!fs.existsSync(tempDir)) {
                fs.mkdirSync(tempDir);
            }

            // Cria arquivo de teste
            fs.writeFileSync(testFile, 'test content');
        });

        afterEach(() => {
            // Remove arquivo de teste
            if (fs.existsSync(testFile)) {
                fs.unlinkSync(testFile);
            }
        });

        it('should process valid image file', async () => {
            const file = {
                path: testFile,
                originalname: 'test.jpg',
                mimetype: 'image/jpeg'
            };

            const result = await processMedia(file, MEDIA_TYPES.IMAGE);
            expect(result).toHaveProperty('buffer');
            expect(result).toHaveProperty('mimetype', 'image/jpeg');
            expect(result).toHaveProperty('filename', 'test.jpg');
            expect(result).toHaveProperty('size');
        });

        it('should throw error for invalid media type', async () => {
            const file = {
                path: testFile,
                originalname: 'test.jpg',
                mimetype: 'image/jpeg'
            };

            await expect(processMedia(file, 'invalid_type')).rejects.toThrow('Tipo de mídia não suportado');
        });

        it('should throw error for invalid file extension', async () => {
            const file = {
                path: testFile,
                originalname: 'test.txt',
                mimetype: 'text/plain'
            };

            await expect(processMedia(file, MEDIA_TYPES.IMAGE)).rejects.toThrow('Extensão de arquivo não permitida');
        });

        it('should throw error for non-existent file', async () => {
            const file = {
                path: 'non-existent.jpg',
                originalname: 'test.jpg',
                mimetype: 'image/jpeg'
            };

            await expect(processMedia(file, MEDIA_TYPES.IMAGE)).rejects.toThrow('Arquivo não encontrado');
        });
    });
}); 