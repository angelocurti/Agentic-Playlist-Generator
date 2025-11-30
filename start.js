// Start script for Render - ensures PORT is properly set
const { spawn } = require('child_process');

const port = process.env.PORT || 3000;

console.log(`Starting Next.js server on port ${port}`);

// Next.js automatically reads PORT from environment
// We just need to pass it explicitly via -p flag
const nextStart = spawn('node', [
  './node_modules/.bin/next',
  'start',
  '-p',
  port.toString()
], {
  stdio: 'inherit',
  env: {
    ...process.env,
    PORT: port.toString()
  }
});

nextStart.on('close', (code) => {
  console.log(`Next.js process exited with code ${code}`);
  process.exit(code);
});

nextStart.on('error', (err) => {
  console.error('Failed to start Next.js:', err);
  process.exit(1);
});

