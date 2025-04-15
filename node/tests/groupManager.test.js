const GroupManager = require('../utils/groupManager');

// Mock do cliente WhatsApp
const mockClient = {
    getChats: jest.fn(),
    getChatById: jest.fn()
};

describe('GroupManager', () => {
    let groupManager;

    beforeEach(() => {
        groupManager = new GroupManager(mockClient);
        jest.clearAllMocks();
    });

    describe('listGroups', () => {
        it('should return list of groups', async () => {
            const mockGroups = [
                {
                    id: { _serialized: 'group1' },
                    isGroup: true,
                    name: 'Group 1',
                    participants: [{}, {}],
                    isGroupAdmin: true,
                    createdAt: new Date()
                },
                {
                    id: { _serialized: 'group2' },
                    isGroup: true,
                    name: 'Group 2',
                    participants: [{}, {}, {}],
                    isGroupAdmin: false,
                    createdAt: new Date()
                }
            ];

            mockClient.getChats.mockResolvedValue(mockGroups);

            const result = await groupManager.listGroups();

            expect(result).toHaveLength(2);
            expect(result[0]).toEqual({
                id: 'group1',
                name: 'Group 1',
                participants: 2,
                isAdmin: true,
                createdAt: expect.any(Date)
            });
        });

        it('should handle errors', async () => {
            mockClient.getChats.mockRejectedValue(new Error('API Error'));

            await expect(groupManager.listGroups()).rejects.toThrow('API Error');
        });
    });

    describe('getGroupInfo', () => {
        it('should return group info', async () => {
            const mockGroup = {
                id: { _serialized: 'group1' },
                isGroup: true,
                name: 'Group 1',
                description: 'Test Group',
                participants: [
                    {
                        id: { _serialized: 'user1' },
                        name: 'User 1',
                        isAdmin: true,
                        isSuperAdmin: false
                    }
                ],
                isGroupAdmin: true,
                createdAt: new Date()
            };

            mockClient.getChatById.mockResolvedValue(mockGroup);

            const result = await groupManager.getGroupInfo('group1');

            expect(result).toEqual({
                id: 'group1',
                name: 'Group 1',
                description: 'Test Group',
                participants: [{
                    id: 'user1',
                    name: 'User 1',
                    isAdmin: true,
                    isSuperAdmin: false
                }],
                isAdmin: true,
                createdAt: expect.any(Date),
                lastUpdated: expect.any(Number)
            });
        });

        it('should throw error for non-group chat', async () => {
            const mockChat = {
                isGroup: false
            };

            mockClient.getChatById.mockResolvedValue(mockChat);

            await expect(groupManager.getGroupInfo('chat1')).rejects.toThrow('Chat não é um grupo');
        });
    });

    describe('sendMessage', () => {
        it('should send text message to group', async () => {
            const mockGroup = {
                isGroup: true,
                sendMessage: jest.fn().mockResolvedValue({
                    id: { _serialized: 'msg1' },
                    timestamp: 1234567890
                })
            };

            mockClient.getChatById.mockResolvedValue(mockGroup);

            const result = await groupManager.sendMessage('group1', 'Hello World');

            expect(result).toEqual({
                success: true,
                messageId: 'msg1',
                timestamp: 1234567890
            });
        });

        it('should send media message to group', async () => {
            const mockGroup = {
                isGroup: true,
                sendImage: jest.fn().mockResolvedValue({
                    id: { _serialized: 'msg1' },
                    timestamp: 1234567890
                })
            };

            mockClient.getChatById.mockResolvedValue(mockGroup);

            const media = {
                type: 'image',
                buffer: Buffer.from('test'),
                filename: 'test.jpg'
            };

            const result = await groupManager.sendMessage('group1', 'Hello World', media);

            expect(result).toEqual({
                success: true,
                messageId: 'msg1',
                timestamp: 1234567890
            });
        });
    });

    describe('participant management', () => {
        const mockGroup = {
            isGroup: true,
            addParticipants: jest.fn().mockResolvedValue({
                added: ['user1'],
                failed: []
            }),
            removeParticipants: jest.fn().mockResolvedValue({
                removed: ['user1'],
                failed: []
            }),
            promoteParticipants: jest.fn().mockResolvedValue({
                promoted: ['user1'],
                failed: []
            }),
            demoteParticipants: jest.fn().mockResolvedValue({
                demoted: ['user1'],
                failed: []
            })
        };

        beforeEach(() => {
            mockClient.getChatById.mockResolvedValue(mockGroup);
        });

        it('should add participants', async () => {
            const result = await groupManager.addParticipants('group1', ['user1']);

            expect(result).toEqual({
                success: true,
                added: ['user1'],
                failed: []
            });
        });

        it('should remove participants', async () => {
            const result = await groupManager.removeParticipants('group1', ['user1']);

            expect(result).toEqual({
                success: true,
                removed: ['user1'],
                failed: []
            });
        });

        it('should promote participants', async () => {
            const result = await groupManager.promoteParticipants('group1', ['user1']);

            expect(result).toEqual({
                success: true,
                promoted: ['user1'],
                failed: []
            });
        });

        it('should demote participants', async () => {
            const result = await groupManager.demoteParticipants('group1', ['user1']);

            expect(result).toEqual({
                success: true,
                demoted: ['user1'],
                failed: []
            });
        });
    });
}); 