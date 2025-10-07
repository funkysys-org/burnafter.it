import apiClient from './client';

const APP_URL = import.meta.env.VITE_APP_URL || 'http://localhost:5173';

export const utilsApi = {
  /**
   * Get QR code image URL
   */
  getQRCodeUrl: (url) => {
    const encodedUrl = encodeURIComponent(url);
    return `${apiClient.defaults.baseURL}/api/utils/qr?url=${encodedUrl}`;
  },

  /**
   * Get full app URL for a shout
   */
  getShoutUrl: (type, hash) => {
    return `${APP_URL}/stream/${type}/${hash}`;
  },

  /**
   * Get full app URL for a chat
   */
  getChatUrl: (hash) => {
    return `${APP_URL}/chat/${hash}`;
  },

  /**
   * Health check
   */
  healthCheck: async () => {
    const response = await apiClient.get('/api/utils/health');
    return response.data;
  },
};
