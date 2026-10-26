import asyncio
import urllib.request
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart

# --- ТОКЕН ТВОЕГО БОТА-АДМИНИСТРАТОРА (ПУЛЬТА) ---
ADMIN_BOT_TOKEN = "8935836134:AAEiK0u9-10cKO4GaIB8n9xYSwulIQPX9Ug".strip()
# --- ТОЧНАЯ ССЫЛКА НА ТВОЙ СЕРВЕР RENDER ---
MAIN_BOT_URL = "https://onrender.com".strip().rstrip('/')

CODE_OWNER = "H1A7T0I8K6"
CODE_TECH_ADMIN = "M3I6S8H1K5O4"

bot = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher()

admin_system = {
    "owner_id": None,
    "tech_admin_id": None,
    "is_tech_allowed": True,
    "main_bot_active": True
}

def get_admin_keyboard(user_id):
    status_text = "🔴 Выключить бота" if admin_system["main_bot_active"] else "🟢 Включить бота"
    allowed_text = "🔒 Блокировать тех. админа" if admin_system["is_tech_allowed"] else "🔓 Разблокировать тех. админа"
    
    buttons = [
        [KeyboardButton(text=status_text), KeyboardButton(text="🔄 Перезагрузить кэш")]
    ]
    if user_id == admin_system["owner_id"]:
        buttons.append([KeyboardButton(text=allowed_text)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_user_role(user_id):
    if user_id == admin_system["owner_id"]:
        return "owner"
    if user_id == admin_system["tech_admin_id"]:
        if admin_system["is_tech_allowed"]:
            return "tech_admin"
        return "blocked"
    return "guest"

# Функция отправки POST-команд через прямое сетевое ядро Render
def send_post_command_to_weather_bot(action_name: str):
    try:
        url = MAIN_BOT_URL
        data = json.dumps({"action": action_name}).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"Content-Type": "application/json", "User-Agent": "AdminBot"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return response.read().decode("utf-8")
    except Exception as e:
        print(f"Ошибка шлюза связи Render: {e}")
    return None

@dp.message(CommandStart())
async def cmd_start(message: Message):
    role = get_user_role(message.from_user.id)
    if role in ["owner", "tech_admin"]:
        await message.answer("🎛 Пульт управления погодным ботом активен!", reply_markup=get_admin_keyboard(message.from_user.id))
    else:
        await message.answer("🔒 Доступ закрыт. Введите секретную код-фразу для авторизации пульта:")

@dp.message(F.text == CODE_OWNER)
async def auth_owner(message: Message):
    admin_system["owner_id"] = message.from_user.id
    await message.answer("👑 Авторизация успешна! Доступ предоставлен Владельцу (Hatik).", reply_markup=get_admin_keyboard(message.from_user.id))

@dp.message(F.text == CODE_TECH_ADMIN)
async def auth_tech_admin(message: Message):
    if not admin_system["is_tech_allowed"]:
        await message.answer("❌ Владелец заблокировал доступ техническим администраторам.")
        return
    admin_system["tech_admin_id"] = message.from_user.id
    await message.answer("🛠 Авторизация успешна! Доступ предоставлен Техническому администратору.", reply_markup=get_admin_keyboard(message.from_user.id))

@dp.message(F.text.in_({"🟢 Включить бота", "🔴 Выключить бота"}))
async def toggle_main_bot(message: Message):
    role = get_user_role(message.from_user.id)
    if role not in ["owner", "tech_admin"]:
        await message.answer("❌ Нет прав.")
        return
        
    res = send_post_command_to_weather_bot("toggle")
    if res:
        admin_system["main_bot_active"] = (res == "active")
        status_str = "ВКЛЮЧЕН" if admin_system["main_bot_active"] else "ВЫКЛЮЧЕН"
        await message.answer(f"🛰 Команда выполнена. Статус изменен на: {status_str}", reply_markup=get_admin_keyboard(message.from_user.id))
    else:
        await message.answer("❌ Ошибка связи: Не удалось достучаться до сервера погодного бота.")

@dp.message(F.text == "🔄 Перезагрузить кэш")
async def clear_main_cache(message: Message):
    role = get_user_role(message.from_user.id)
    if role not in ["owner", "tech_admin"]:
        await message.answer("❌ Нет прав.")
        return
        
    res = send_post_command_to_weather_bot("clear")
    if res == "cleared":
        await message.answer("🛰 Кэш погодных данных успешно сброшен!")
    else:
        await message.answer("❌ Ошибка сброса кэша. Сервер недоступен.")

@dp.message(F.text.in_({"🔒 Блокировать тех. админа", "🔓 Разблокировать тех. админа"}))
async def lock_tech_admin(message: Message):
    if get_user_role(message.from_user.id) != "owner":
        await message.answer("❌ Только Владелец (Hatik) может изменять права тех. админа.")
        return
    admin_system["is_tech_allowed"] = not admin_system["is_tech_allowed"]
    res_text = "🔒 Тех. администратор заблокирован!" if not admin_system["is_tech_allowed"] else "🔓 Тех. администратор разблокирован!"
    await message.answer(res_text, reply_markup=get_admin_keyboard(message.from_user.id))

# Веб-заглушка для прохождения проверки портов Render для пульта
class AdminHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_admin_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), AdminHealthHandler)
    server.serve_forever()

async def main():
    threading.Thread(target=run_admin_server, daemon=True).start()
    print("🚀 Исторический Бот-Пульт успешно запущен на Render!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
