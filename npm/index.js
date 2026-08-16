#!/usr/bin/env node

const { spawn } = require('child_process');

const args = ['--from', 'daily-ai-brief', 'daily-ai-brief', ...process.argv.slice(2)];

const child = spawn('uvx', args, {
  stdio: 'inherit'
});

child.on('error', (err) => {
  console.error('Failed to start uvx:', err.message);
  console.error('Please ensure uv is installed: https://docs.astral.sh/uv/getting-started/installation/');
  process.exit(1);
});

child.on('exit', (code) => {
  process.exit(code || 0);
});
