const express = require('express');
const { spawn } = require('child_process');
const bodyParser = require('body-parser');
const dotenv = require('dotenv');

dotenv.config();

const {
  BOT_TOKEN,
  PORT
} = process.env;

const app = express();
const portNumber = process.env.PORT || 3000;

app.use(bodyParser.json());

let botProcess;

function startBot() {
  botProcess = spawn('python', ['bot_logic.py']);

  botProcess.stdout.on('data', (data) => {
    console.log(`Bot output: ${data}`);
  });

  botProcess.stderr.on('data', (data) => {
    console.error(`Bot error: ${data}`);
  });

  botProcess.on('close', (code) => {
    console.log(`Bot process exited with code ${code}`);
    // Restart the bot if it crashes
    setTimeout(startBot, 5000);
  });
}

app.post(`/webhook/${BOT_TOKEN}`, (req, res) => {
  // Forward the webhook data to the Python bot
  if (botProcess && botProcess.stdin.writable) {
    botProcess.stdin.write(JSON.stringify(req.body) + '\n');
  }
  res.sendStatus(200);
});

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK' });
});

app.listen(portNumber, '0.0.0.0', () => {
  console.log(`Server running on port ${portNumber}`);
  startBot();
});

process.on('SIGTERM', () => {
  if (botProcess) {
    botProcess.kill();
  }
  process.exit(0);
});

