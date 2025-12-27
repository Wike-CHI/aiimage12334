module.exports = {
  apps: [{
    name: 'white-bg-backend',
    script: 'uvicorn',
    args: 'app.main:app --host 0.0.0.0 --port 55555',
    cwd: '/www/wwwroot/生图网站/aiimage12334/backend',
    interpreter: 'python3',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      PYTHONPATH: '/www/wwwroot/生图网站/aiimage12334/backend',
      DB_HOST: 'localhost',
      DB_PORT: 3306,
      DB_USER: 'root',
      DB_PASSWORD: '123456',
      DB_NAME: 'white_bg_generator',
      GEMINI_API_KEY: 'sk-9pI1g5gQqtCuvbzOE0Fb3467901b4cAb801f1cE333F27886',
      SECRET_KEY: 'your-secret-key-change-in-production',
      ALGORITHM: 'HS256',
      ACCESS_TOKEN_EXPIRE_MINUTES: 30,
      FRONTEND_URL: 'http://129.211.218.135:34345'
    }
  }]
};
