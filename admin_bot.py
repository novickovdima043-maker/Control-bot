import asyncio
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart

# --- ТОКЕН ТВОЕГО БОТА-АДМИНИСТРАТОРА (КОНТРОЛЬНОГО) ---
ADMIN_BOT_TOKEN = "8935836134:AAEiK0u9-10cKO4GaIB8n9xYSwulIQPX9Ug".strip()
# --- ССЫЛКА НА ТВОЕГО ПОГОДНОГО БОТА С САЙТА RENDER ---
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
        [KeyboardButton(text=status_text), KeyboardButton(text="🔄 Перезагрузить кэш")],
        [KeyboardButton(text="🚪 Выход из аккаунта")]
    ]
    if user_id == admin_system["owner_id"]:
        buttons.insert(1, [KeyboardButton(text=allowed_text)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_user_role(user_id):
    if user_id == admin_system["owner_id"]: return "owner"
    if user_id == admin_system["tech_admin_id"]:
        return "tech_admin" if admin_system["is_tech_allowed"] else "blocked"
    return "guest"

# Функция отправки сигнала на сервер Render погодного бота
def call_render_gateway(endpoint: str):
    try:
        url = f"{MAIN_BOT_URL}{endpoint}"
        req = urllib.request.Request(url, headers={"User-Agent": "AdminBot"})
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                return response.read().decode("utf-8")
    except Exception as e:
        print(f"Ошибка связи: {e}")
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
    if role not in ["owner", "tech_admin"]: return
        
    cmd = "/toggle_off" if admin_system["main_bot_active"] else "/toggle_on"
    res = call_render_gateway(cmd)
    
    if res:
        admin_system["main_bot_active"] = (res == "active")
        if admin_system["main_bot_active"]:
            await message.answer("🟢 Погодный бот успешно переведен в статус: ВКЛЮЧЕН. Отправлено уведомление: 'Бот снова работает'", reply_markup=get_admin_keyboard(message.from_user.id))
        else:
            await message.answer("🔴 Погодный бот успешно переведен в статус: ВЫКЛЮЧЕН. Отправлено уведомление: 'Бот выключен по техническим обстоятельствам'", reply_markup=get_admin_keyboard(message.from_user.id))
    else:
        await message.answer("❌ Ошибка связи: Не удалось достучаться до сервера погодного бота на Render.")

@dp.message(F.text == "🔄 Перезагрузить кэш")
async def clear_main_cache(message: Message):
    role = get_user_role(message.from_user.id)
    if role not in ["owner", "tech_admin"]: return
        
    res = call_render_gateway("/clear_cache")
    if res == "cleared":
        await message.answer("🛰 Сигнал очистки кэша успешно выполнен на сервере!")
    else:
        await message.answer("❌ Ошибка сброса кэша.")

@dp.message(F.text == "🚪 Выход из аккаунта")
async def process_logout(message: Message):
    role = get_user_role(message.from_user.id)
    if role == "owner": admin_system["owner_id"] = None
    elif role == "tech_admin": admin_system["tech_admin_id"] = None
    await message.answer("🔒 Вы успешно вышли. Введите код-фразу для входа:", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text.in_({"🔒 Блокировать тех. админа", "🔓 Разблокировать тех. админа"}))
async def lock_tech_admin(message: Message):
    if get_user_role(message.from_user.id) != "owner": return
    admin_system["is_tech_allowed"] = not admin_system["is_tech_allowed"]
    res_text = "🔒 Тех. администратор заблокирован!" if not admin_system["is_tech_allowed"] else "🔓 Тех. администратор разблокирован!"
    await message.answer(res_text, reply_markup=get_admin_keyboard(message.from_user.id))

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
    print("🚀 Бот-Пульт v1.4 успешно запущен на Render!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
