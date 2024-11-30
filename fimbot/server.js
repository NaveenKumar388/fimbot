const express = require('express');
const { spawn } = require('child_process');
const bodyParser = require('body-parser');
const dotenv = require('dotenv');

dotenv.config();

const {
  BOT_TOKEN,
  OWNER_UPI_ID,
  MAILGUN_API_KEY,
  MAILGUN_DOMAIN,
  RECIPIENT_EMAIL,
  PORT
} = process.env;

const app = express();
const portNumber = PORT || 3000;

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

app.post('/webhook', (req, res) => {
  // Forward the webhook data to the Python bot
  if (botProcess && botProcess.stdin.writable) {
    botProcess.stdin.write(JSON.stringify(req.body) + '\n');
  }
  res.sendStatus(200);
});

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK' });
});

// Add this new route to set the webhook
app.get('/setwebhook', async (req, res) => {
  const webhookUrl = `https://${req.get('host')}/webhook`;
  const setWebhookUrl = `https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${webhookUrl}`;
  
  try {
    const response = await fetch(setWebhookUrl);
    const data = await response.json();
    if (data.ok) {
      res.send('Webhook set successfully');
    } else {
      res.status(400).send('Failed to set webhook');
    }
  } catch (error) {
    console.error('Error setting webhook:', error);
    res.status(500).send('Error setting webhook');
  }
});

app.listen(portNumber, () => {
  console.log(`Server running on port ${portNumber}`);
  startBot();
});

process.on('SIGTERM', () => {
  if (botProcess) {
    botProcess.kill();
  }
  process.exit(0);
});

