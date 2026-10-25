import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart

# --- ВШИТЫЕ ТОКЕНЫ ОБОИХ БОТОВ (v0.6.1) ---
ADMIN_BOT_TOKEN = "8935836134:AAHHM50zxjn7xu0gu3zaNQWJWFdUBOjcl7M".strip()
MAIN_BOT_TOKEN = "8828936622:AAEDwEvUNu7KA0sM_Jv4VNEP8CEalwnOH3g".strip()

CODE_OWNER = "H1A7T0I8K6"
CODE_TECH_ADMIN = "M3I6S8H1K5O4"

bot = Bot(token=ADMIN_BOT_TOKEN)
main_bot_client = Bot(token=MAIN_BOT_TOKEN)  # Клиент для отправки команд в погодный бот
dp = Dispatcher()

admin_system = {
    "owner_id": None,
    "tech_admin_id": None,
    "is_tech_admin_allowed": True,
    "main_bot_active": True
}

def get_admin_keyboard(user_id):
    status_text = "🔴 Выключить бота" if admin_system["main_bot_active"] else "🟢 Включить бота"
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
        
    signal = "_sys_toggle_off_" if admin_system["main_bot_active"] else "_sys_toggle_on_"
    
    try:
        # Отправляем скрытую команду напрямую по твоему Telegram ID (от лица погодного бота)
        await main_bot_client.send_message(chat_id=message.from_user.id, text=signal)
        admin_system["main_bot_active"] = not admin_system["main_bot_active"]
        await message.answer("🛰 Команда успешно передана через шлюз Telegram API!", reply_markup=get_admin_keyboard(message.from_user.id))
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки сигнала через Telegram API: {e}")

@dp.message(F.text == "🔄 Перезагрузить кэш")
async def clear_main_cache(message: Message):
    role = get_user_role(message.from_user.id)
    if role not in ["owner", "tech_admin"]:
        await message.answer("❌ Нет прав.")
        return
        
    try:
        await main_bot_client.send_message(chat_id=message.from_user.id, text="_sys_clear_cache_")
        await message.answer("🛰 Сигнал очистки кэша успешно передан погодному боту!")
    except Exception as e:
        await message.answer(f"❌ Ошибка сброса кэша: {e}")

@dp.message(F.text == "🚪 Выход из аккаунта")
async def process_logout(message: Message):
    role = get_user_role(message.from_user.id)
    if role == "owner":
        admin_system["owner_id"] = None
    elif role == "tech_admin":
        admin_system["tech_admin_id"] = None
    await message.answer("🔒 Вы успешно вышли. Введите код-фразу для входа:", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text.in_({"🔒 Блокировать тех. админа", "🔓 Разблокировать тех. админа"}))
async def lock_tech_admin(message: Message):
    if get_user_role(message.from_user.id) != "owner":
        await message.answer("❌ Отказано в доступе.")
        return
    admin_system["is_tech_admin_allowed"] = not admin_system["is_tech_admin_allowed"]
    res_text = "🔒 Тех. администратор заблокирован!" if not admin_system["is_tech_admin_allowed"] else "🔓 Тех. администратор разблокирован!"
    await message.answer(res_text, reply_markup=get_admin_keyboard(message.from_user.id))

async def main():
    print("🚀 Облачный Бот-Пульт v0.6.1 запущен на Render!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
