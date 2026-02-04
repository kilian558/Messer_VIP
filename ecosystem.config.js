module.exports = {
  apps: [{
    name: 'messer-vip-bot',
    script: 'main.py',
    interpreter: './venv/bin/python3',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    max_restarts: 10,
    min_uptime: '10s',
    env: {
      NODE_ENV: 'production',
      PYTHONUNBUFFERED: '1'
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    time: true,
    kill_timeout: 5000,
    restart_delay: 4000,
    exp_backoff_restart_delay: 100
  }]
};
