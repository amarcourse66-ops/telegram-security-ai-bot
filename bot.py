

import os
import telebot

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "أهلاً فيك ❤️ أنا بوتك الخاص!")

@bot.message_handler(func=lambda message: True)
def reply(message):
    bot.reply_to(message, "وصلتني رسالتك ❤️")

bot.infinity_polling()
