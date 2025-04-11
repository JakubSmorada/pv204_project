import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000';

const api = {
  getChallenge: () => {
    return axios.get(`${API_URL}/users/challenge`);
  },
  
  registerUser: (userData, token) => {
    return axios.post(`${API_URL}/users/register?token=${token}`, userData);
  }
};

export default api;