require("dotenv").config();
const { Client, LocalAuth } = require("whatsapp-web.js");
const axios = require("axios");
const qrcode = require("qrcode-terminal");
const FormData = require("form-data");
const MAX_QUEUE_SIZE = process.env.MAX_QUEUE_SIZE || 10;
const ATTENDANCE_TIMEOUT = 15 * 60 * 1000; // 15 minutes in milliseconds
const DEEPSEEK_TIMEOUT = 5 * 60 * 1000; // 5 minutes in milliseconds

const client = new Client({
  authStrategy: new LocalAuth()
});

let isChecking = false; // 🔒 Lock flag
let deepSeekQueue = []; // Queue for DeepSeek requests
let isProcessingDeepSeek = false; // 🔒 Lock flag for DeepSeek

// 🤖 DeepSeek API call
async function askDeepSeek(userMessage) {
  const res = await axios.post(
    "https://openrouter.ai/api/v1/chat/completions",
    {
      model: "deepseek/deepseek-r1:free",
      messages: [
        {
          role: "system",
          content:
            process.env.DEEPSEEK_CONTEXT || "You are a helpful assistant."
        },
        // tell the system to not to use any markdown formatting, just use format that whatsapp supports by maintaining the information structure
        {
          role: "system",
          content:
            "Please respond in plain text without any markdown formatting."
        },
        {
          role: "user",
          content: userMessage
        }
      ]
    },
    {
      headers: {
        Authorization: `Bearer ${process.env.DEEPSEEK_API_KEY}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "DeepSeek Chat"
      },
      timeout: DEEPSEEK_TIMEOUT
    }
  );
  return res.data.choices?.[0]?.message?.content;
}

// 📋 Process DeepSeek queue
async function processDeepSeekQueue() {
  if (isProcessingDeepSeek || deepSeekQueue.length === 0 || isChecking) return;

  isProcessingDeepSeek = true;
  const { msg, userQuestion } = deepSeekQueue.shift();

  // Set timeout for DeepSeek processing
  const deepSeekTimeout = setTimeout(() => {
    if (isProcessingDeepSeek) {
      isProcessingDeepSeek = false;
      msg.reply(
        "⏰ AI request timed out after 5 minutes. Please try again with a shorter question."
      );
      // Continue processing queue
      setTimeout(processDeepSeekQueue, 100);
    }
  }, DEEPSEEK_TIMEOUT);

  try {
    const reply = await askDeepSeek(userQuestion);
    if (reply) {
      msg.reply("🤖 *AI Response:*\n\n" + reply);
    } else {
      msg.reply("❌ Received empty response from AI. Please try again.");
    }
  } catch (error) {
    console.error("DeepSeek API Error:", error);
    if (error.code === "ECONNABORTED") {
      msg.reply(
        "⏰ AI request timed out. Please try again with a shorter question."
      );
    } else if (error.response?.status === 429) {
      msg.reply("⚠️ Rate limit exceeded. Please try again later.");
    } else {
      msg.reply("❌ Error processing AI request. Please try again later.");
    }
  } finally {
    clearTimeout(deepSeekTimeout);
    isProcessingDeepSeek = false;
    setTimeout(processDeepSeekQueue, 100);
  }
}

client.on("qr", (qr) => {
  qrcode.generate(qr, { small: true });
});

client.on("ready", () => {
  console.log("WhatsApp bot is ready!");
});

client.on("message", async (msg) => {
  if (msg.body.toLowerCase().includes("ancis presensi kkn")) {
    if (isChecking) {
      msg.reply("⏳ A check is already in progress. Please wait...");
      return;
    }

    isChecking = true; // Lock
    msg.reply("⏳ Checking KKN attendance...");

    const attendanceTimeout = setTimeout(() => {
      if (isChecking) {
        isChecking = false;
        msg.reply(
          "⏰ Attendance check timed out after 15 minutes. Please try again."
        );
      }
    }, ATTENDANCE_TIMEOUT);

    try {
      const form = new FormData();
      form.append("username", process.env.UGM_USERNAME);
      form.append("password", process.env.UGM_PASSWORD);

      const response = await axios.post(process.env.API_URL, form, {
        headers: form.getHeaders(),
        timeout: ATTENDANCE_TIMEOUT
      });

      const data = response.data.results;
      const absent = data.filter((d) => d.status === "absent");
      const present = data.filter((d) => d.status === "present");

      let reply = `📋 *KKN Attendance Summary* (${data[0].date})\n\n`;
      reply += `❌ Absent: ${absent.length}\n✅ Present: ${present.length}\n\n`;

      if (absent.length > 0) {
        reply += `*Absent Students:*\n`;
        absent.forEach((s, i) => {
          reply += `${i + 1}. ${s.name} (${s.student_id})\n`;
        });
        reply += `\n`;
      }

      if (present.length > 0) {
        present.sort((a, b) => {
          if (!a.time) return 1;
          if (!b.time) return -1;
          return a.time.localeCompare(b.time);
        });

        reply += `*Present Students (GMT+07:00):*\n`;
        present.forEach((s, i) => {
          const timeStr = s.time ? ` at ${s.time}` : "";
          reply += `${i + 1}. ${s.name} (${s.student_id})${timeStr}\n`;
        });
      }

      msg.reply(reply);
    } catch (err) {
      console.error(err);
      if (err.code === "ECONNABORTED") {
        msg.reply("⏰ Attendance check timed out. Please try again.");
      } else {
        msg.reply("❌ Error checking attendance. Please try again later.");
      }
    } finally {
      clearTimeout(attendanceTimeout); // Fixed: Clear timeout in finally block
      isChecking = false; // 🔓 Unlock
    }
  }
  // 🤖 DeepSeek chat functionality
  else if (msg.body.toLowerCase().startsWith("ask ai:")) {
    const userQuestion = msg.body.slice(7).trim(); // Extract question after "ask ai:"
    if (!userQuestion) {
      msg.reply("❌ Please provide a question for the AI.");
      return;
    }

    // Check if attendance checking is in progress
    if (isChecking) {
      msg.reply(
        "⚠️ Server is busy! Attendance checking is currently in progress. Please wait until it completes."
      );
      return;
    }

    // Check if queue is full
    if (deepSeekQueue.length >= MAX_QUEUE_SIZE) {
      msg.reply(
        "⚠️ Server is busy! Queue is full (10/10). Please wait until the server is not busy and try again later."
      );
      return;
    }

    // Add to queue
    deepSeekQueue.push({ msg, userQuestion });
    const queuePosition = deepSeekQueue.length;

    if (queuePosition === 1 && !isProcessingDeepSeek) {
      msg.reply("🤖 Processing your question...");
      processDeepSeekQueue();
    } else {
      msg.reply(
        `⏳ Your request has been queued. Position: ${queuePosition}/10\nPlease wait...`
      );
    }
  }
});

client.initialize();
