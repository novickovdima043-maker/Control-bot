
import asyncio
import urllib.request
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart

# --- ВШИТЫЕ ДАННЫЕ АДМИН-ПУЛЬТА (v0.5.1) ---
ADMIN_BOT_TOKEN = "8935836134:AAHHM50zxjn7xu0gu3zaNQWJWFdUBOjcl7M".strip()
MAIN_BOT_URL = "https://onrender.com".strip().rstrip('/')

CODE_OWNER = "H1A7T0I8K6"
CODE_TECH_ADMIN = "M3I6S8H1K5O4"

bot = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher()

admin_system = {
    "owner_id": None,
    "tech_admin_id": None,
    "is_tech_admin_allowed": True
}

# Кнопка статистики полностью удалена, добавлена кнопка Выхода
def get_admin_keyboard(user_id, is_active=True):
    status_text = "🔴 Выключить бота" if is_active else "🟢 Включить бота"
    allowed_text = "🔒 Блокировать тех. админа" if admin_system["is_tech_admin_allowed"] else "🔓 Разблокировать тех. админа"
    
    buttons = [
        [KeyboardButton(text=status_text), KeyboardButton(text="🔄 Перезагрузить кэш")],
        [KeyboardButton(text="🚪 Выход из аккаунта")]
    ]
    if user_id == admin_system["owner_id"]:
        buttons.insert(1, [KeyboardButton(text=allowed_text)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_user_role(user_id):
    if user_id == admin_system["owner_id"]:
        return "owner"
    if user_id == admin_system["tech_admin_id"]:
        if admin_system["is_tech_admin_allowed"]:
            return "tech_admin"
        return "blocked"
    return "guest"

def send_command_to_main_bot(endpoint: str):
    try:
        url = f"{MAIN_BOT_URL}{endpoint}"
        req = urllib.request.Request(url, headers={"User-Agent": "AdminBot"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return response.read().decode("utf-8")
    except Exception as e:
        print(f"Ошибка шлюза связи: {e}")
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
    if not admin_system["is_tech_admin_allowed"]:
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
    res = send_command_to_main_bot("/toggle")
    if res:
        is_active = (res == "active")
        status_str = "ВКЛЮЧЕН" if is_active else "ВЫКЛЮЧЕН"
        await message.answer(f"📢 Основной погодный бот успешно {status_str}!", reply_markup=get_admin_keyboard(message.from_user.id, is_active))
    else:
        await message.answer("❌ Не удалось связаться с сервером погодного бота.")

@dp.message(F.text == "🔄 Перезагрузить кэш")
async def clear_main_cache(message: Message):
    role = get_user_role(message.from_user.id)
    if role not in ["owner", "tech_admin"]:
        await message.answer("❌ Нет прав.")
        return
    res = send_command_to_main_bot("/clear")
    if res == "cleared":
        await message.answer("🔄 Кэш погодных данных на сервере успешно сброшен!")
    else:
        await message.answer("❌ Сервер погодного бота недоступен.")

# --- НОВАЯ ОПЕРАЦИЯ: ЛОГАУТ / ВЫХОД ИЗ СЕССИИ ---
@dp.message(F.text == "🚪 Выход из аккаунта")
async def process_logout(message: Message):
    user_id = message.from_user.id
    role = get_user_role(user_id)
    
    if role == "guest":
        await message.answer("❌ Вы не авторизованы.")
        return
        
    # Стираем сессию в зависимости от того, кто выходит
    if role == "owner":
        admin_system["owner_id"] = None
        print(f"LOG: Владелец {user_id} вышел из аккаунта.")
    elif role == "tech_admin":
        admin_system["tech_admin_id"] = None
        print(f"LOG: Технический админ {user_id} вышел из аккаунта.")
        
    # Удаляем клавиатуру пульта и блокируем доступ
    await message.answer(
        "🔒 Вы успешно вышли из панели управления.\nСессия закрыта. Для повторного входа введите код-фразу:",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(F.text.in_({"🔒 Блокировать тех. админа", "🔓 Разблокировать тех. админа"}))
async def lock_tech_admin(message: Message):
    if get_user_role(message.from_user.id) != "owner":
        await message.answer("❌ Только Владелец (Hatik) может заблокировать тех. админа.")
        return
    admin_system["is_tech_admin_allowed"] = not admin_system["is_tech_admin_allowed"]
    res_text = "🔒 Тех. администратор заблокирован!" if not admin_system["is_tech_admin_allowed"] else "🔓 Тех. администратор разблокирован!"
    await message.answer(res_text, reply_markup=get_admin_keyboard(message.from_user.id))

class AdminHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Admin panel is alive")

def run_admin_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), AdminHealthHandler)
    server.serve_forever()

async def main():
    threading.Thread(target=run_admin_server, daemon=True).start()
    print("🚀 Отдельный облачный Бот-Пульт успешно обновлен до v0.5.1!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
