const express = require("express");
const { spawn } = require("child_process");
const bodyParser = require("body-parser");
const dotenv = require("dotenv");
dotenv.config();

const PORT = process.env.PORT || 8080;

const app = express();
app.use(bodyParser.json());

let botProcess;

function startBot() {
  botProcess = spawn("python", ["bot_logic.py"]);

  botProcess.stdout.on("data", (data) => {
    console.log(`Bot output: ${data}`);
  });

  botProcess.stderr.on("data", (data) => {
    console.error(`Bot error: ${data}`);
  });

  botProcess.on("close", (code) => {
    console.log(`Bot process exited with code ${code}`);
    setTimeout(startBot, 5000); // Restart bot after a crash
  });
}

app.get("/health", (req, res) => {
  res.status(200).json({ status: "OK" });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  startBot();
});

process.on("SIGTERM", () => {
  if (botProcess) {
    botProcess.kill();
  }
  process.exit(0);
});
