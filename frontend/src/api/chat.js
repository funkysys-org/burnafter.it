import apiClient from './client';

export const chatApi = {
  /**
   * Create a new chat room
   */
  createChatRoom: async () => {
    const response = await apiClient.post('/api/chat/create');
    return response.data;
  },

  /**
   * Get chat room details
   */
  getChatRoom: async (hash) => {
    const response = await apiClient.get(`/api/chat/${hash}`);
    return response.data;
  },

  /**
   * Get all messages in a chat room
   */
  getChatMessages: async (hash) => {
    const response = await apiClient.get(`/api/chat/${hash}/messages`);
    return response.data;
  },

  /**
   * Post a message to a chat room
   */
  postChatMessage: async (hash, data) => {
    const formData = new FormData();
    formData.append('type', data.type);
    formData.append('maxhits', data.maxhits || 10);
    formData.append('maxtime', data.maxtime || 5);

    if (data.type === 'text') {
      formData.append('data', data.content);
    } else if (data.file) {
      formData.append('data', data.file);
    } else if (data.content) {
      formData.append('data', data.content);
    }

    const response = await apiClient.post(`/api/chat/${hash}/message`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
