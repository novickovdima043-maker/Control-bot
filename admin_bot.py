import asyncio
import urllib.request
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

# --- ВШИТЫЙ ТОКЕН ТВОЕГО БОТА-АДМИНИСТРАТОРА ---
ADMIN_BOT_TOKEN = "8935836134:AAHHM50zxjn7xu0gu3zaNQWJWFdUBOjcl7M".strip()
# --- ВШИТАЯ ПЕРСОНАЛЬНАЯ ССЫЛКА НА ТВОЙ СЕРВЕР RENDER ---
MAIN_BOT_URL = "https://my-weather-bot-8zr1.onrender.com".strip().rstrip('/')

CODE_OWNER = "H1A7T0I8K6"
CODE_TECH_ADMIN = "M3I6S8H1K5O4"

bot = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher()

admin_system = {
    "owner_id": None,
    "tech_admin_id": None,
    "is_tech_admin_allowed": True
}

def get_admin_keyboard(user_id, is_active=True):
    status_text = "🔴 Выключить бота" if is_active else "🟢 Включить бота"
    allowed_text = "🔒 Блокировать тех. админа" if admin_system["is_tech_admin_allowed"] else "🔓 Разблокировать тех. админа"
    
    buttons = [
        [KeyboardButton(text=status_text), KeyboardButton(text="🔄 Перезагрузить кэш")],
        [KeyboardButton(text="📊 Посмотреть статистику")]
    ]
    if user_id == admin_system["owner_id"]:
        buttons.append([KeyboardButton(text=allowed_text)])
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
        print(f"Ошибка связи с погодным ботом: {e}")
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
        await message.answer("❌ Не удалось связаться с сервером основного погодного бота.")

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

@dp.message(F.text == "📊 Посмотреть статистику")
async def get_main_stats(message: Message):
    role = get_user_role(message.from_user.id)
    if role not in ["owner", "tech_admin"]:
        await message.answer("❌ Нет прав.")
        return
        
    res = send_command_to_main_bot("/status")
    if res:
        data = json.loads(res)
        status_str = "Работает 🟢" if data["status"] == "active" else "Отключен 🔴"
        await message.answer(f"📊 **Статистика @weather145_bot:**\n─────────────────────\n⚙️ Статус: {status_str}\n👥 Уникальных юзеров в базе: `{data['users']}`\n─────────────────────")
    else:
        await message.answer("❌ Ошибка связи: Не удалось стянуть статистику.")

@dp.message(F.text.in_({"🔒 Блокировать тех. админа", "🔓 Разблокировать тех. админа"}))
async def lock_tech_admin(message: Message):
    if get_user_role(message.from_user.id) != "owner":
        await message.answer("❌ Только Владелец (Hatik) может заблокировать тех. админа.")
        return
        
    admin_system["is_tech_admin_allowed"] = not admin_system["is_tech_admin_allowed"]
    res_text = "🔒 Тех. администратор заблокирован!" if not admin_system["is_tech_admin_allowed"] else "🔓 Тех. администратор разблокирован!"
    await message.answer(res_text, reply_markup=get_admin_keyboard(message.from_user.id))

async def main():
    print("🚀 Отдельный Бот-Пульт успешно запущен на твоем ПК!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
