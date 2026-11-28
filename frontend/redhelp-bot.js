import { Telegraf, Markup } from 'telegraf';

// Token copied directly from your BotFather setup
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || '9170799311:AAFB1HNSzIlD00yg5Wsc9XbuUfzaF3E0HE4';
const MINI_APP_URL = process.env.MINI_APP_URL || 'https://red-help-interpise-system-project.vercel.app'; 

const bot = new Telegraf(BOT_TOKEN);

bot.start((ctx) => {
  const welcomeText = 
`👋 *Welcome to Red Cloud Enterprise Operations!*

Centralized real-time database monitoring, server telemetry, perimeter defense, and RAG AI intelligence.

Tap the button below to launch the entire platform inside Telegram:`;

  const launchUrl = `${MINI_APP_URL}?telegram_chat_id=${ctx.chat.id}`;

  return ctx.replyWithMarkdown(
    welcomeText,
    Markup.inlineKeyboard([
      [Markup.button.webApp('🚀 Launch Red Cloud Platform', launchUrl)]
    ])
  );
});

bot.on('text', (ctx) => {
  const launchUrl = `${MINI_APP_URL}?telegram_chat_id=${ctx.chat.id}`;
  return ctx.replyWithMarkdown(
    `Click the button below to open the Red Cloud platform:`,
    Markup.inlineKeyboard([
      [Markup.button.webApp('🚀 Launch Red Cloud Platform', launchUrl)]
    ])
  );
});

// Automatically update Telegram's bottom menu button on startup
bot.telegram.setChatMenuButton({
  menuButton: {
    type: 'web_app',
    text: '🚀 Launch Red Cloud',
    web_app: { url: MINI_APP_URL }
  }
}).then(() => console.log('✅ Bottom menu button URL updated in Telegram!'))
  .catch(err => console.warn('⚠️ Failed to set chat menu button:', err));

bot.launch().then(() => console.log('🤖 RedCloud Bot is live and listening!'));

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
