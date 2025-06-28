require("dotenv").config();
const { Client, LocalAuth } = require("whatsapp-web.js");
const axios = require("axios");
const qrcode = require("qrcode-terminal");
const FormData = require("form-data");

const client = new Client({
  authStrategy: new LocalAuth()
});

client.on("qr", (qr) => {
  qrcode.generate(qr, { small: true });
});

client.on("ready", () => {
  console.log("WhatsApp bot is ready!");
});

client.on("message", async (msg) => {
  if (msg.body.toLowerCase().includes("presensi kkn")) {
    msg.reply("⏳ Checking KKN attendance...");

    try {
      // Create the form data
      const form = new FormData();
      form.append("username", process.env.UGM_USERNAME);
      form.append("password", process.env.UGM_PASSWORD);

      const response = await axios.post(process.env.API_URL, form, {
        headers: form.getHeaders()
      });

      const data = response.data.results;
      const absent = data.filter((d) => d.status === "absent");
      const present = data.filter((d) => d.status === "present");

      let reply = `📋 *KKN Attendance Summary* (${data[0].date})\n\n`;
      reply += `✅ Present: ${present.length}\n❌ Absent: ${absent.length}\n\n`;
      if (absent.length > 0) {
        reply += `*Absent Students:*\n`;
        absent.forEach((s) => {
          reply += `- ${s.name} (${s.student_id})\n`;
        });
      }

      msg.reply(reply);
    } catch (err) {
      console.error(err);
      msg.reply("⚠️ Error checking attendance.");
    }
  }
});

client.initialize();
