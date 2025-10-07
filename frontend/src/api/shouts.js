import apiClient from './client';

export const shoutApi = {
  /**
   * Create a new shout
   */
  createShout: async (data) => {
    const formData = new FormData();
    formData.append('type', data.type);
    formData.append('maxhits', data.maxhits || 1);
    formData.append('maxtime', data.maxtime || 240);

    if (data.type === 'text') {
      formData.append('data', data.content);
      const response = await apiClient.post('/api/shouts/create', formData);
      return response.data;
    } else {
      // For media files
      if (data.file) {
        formData.append('data', data.file);
      } else if (data.content) {
        // For base64 encoded content (photos from canvas)
        formData.append('data', data.content);
      }

      const response = await apiClient.post('/api/shouts/create', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    }
  },

  /**
   * Get a shout by hash
   */
  getShout: async (hash, preview = false) => {
    const params = preview ? { preview: '1' } : {};
    const response = await apiClient.get(`/api/shouts/${hash}`, { params });
    return response.data;
  },

  /**
   * Check if a shout exists
   */
  checkShout: async (hash) => {
    const response = await apiClient.get(`/api/shouts/check/${hash}`);
    return response.data;
  },
};
