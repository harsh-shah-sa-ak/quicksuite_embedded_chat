// Environment configuration for different deployment environments
const config = {
  development: {
    API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8004'
  },
  production: {
    API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8004'
  }
};

const environment = import.meta.env.MODE || 'development';


console.log('Environment:', environment);
console.log('VITE_API_BASE_URL:', import.meta.env.VITE_API_BASE_URL);
console.log('Config:', config[environment]);

export default config[environment];
