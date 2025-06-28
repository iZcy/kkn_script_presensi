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
  if (msg.body.toLowerCase().includes("ancis presensi kkn")) {
    msg.reply("⏳ Checking KKN attendance...");

    try {
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
      reply += `❌ Absent: ${absent.length}\n✅ Present: ${present.length}\n\n`;

      if (absent.length > 0) {
        reply += `*Absent Students:*\n`;
        absent.forEach((s, i) => {
          reply += `${i + 1}. ${s.name} (${s.student_id})\n`;
        });
        reply += `\n`;
      }

      if (present.length > 0) {
        // Sort by time (earliest first)
        present.sort((a, b) => {
          if (!a.time) return 1;
          if (!b.time) return -1;
          return a.time.localeCompare(b.time); // time is in string format like "08:45"
        });

        reply += `*Present Students:*\n`;
        present.forEach((s, i) => {
          const timeStr = s.time ? ` at ${s.time}` : "";
          reply += `${i + 1}. ${s.name} (${s.student_id})${timeStr}\n`;
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
