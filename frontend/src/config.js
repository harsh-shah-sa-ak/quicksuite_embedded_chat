// Environment configuration for different deployment environments
const config = {
  development: {
    API_BASE_URL: 'http://localhost:8000'
  },
  production: {
    API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'https://api.yourdomain.com'
  }
};

const environment = import.meta.env.MODE || 'development';

export default config[environment];
