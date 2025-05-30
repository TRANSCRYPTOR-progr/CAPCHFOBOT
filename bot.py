import os
import json
import random
import string
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, ChatMemberUpdatedFilter, ADMINISTRATOR
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from PIL import Image, ImageDraw
import io
import asyncio

load_dotenv()

bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()

SETTINGS_FILE = 'bot_settings.json'

users_data = {}
used_links = {}
channel_id = None

def load_settings():
    global channel_id
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                channel_id = settings.get('channel_id')
    except Exception as e:
        print(f"Ошибка при загрузке настроек: {e}")

def save_settings():
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump({'channel_id': channel_id}, f)
    except Exception as e:
        print(f"Ошибка при сохранении настроек: {e}")

load_settings()

def generate_captcha():
    # Генерируем случайный текст капчи
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    # Создаем изображение
    width = 400
    height = 120
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Рисуем текст
    text_x = 50
    text_y = 35
    
    # Рисуем каждую букву отдельно с случайным сдвигом
    for char in captcha_text:
        # Случайный сдвиг
        x = text_x + random.randint(-5, 5)
        y = text_y + random.randint(-5, 5)
        
        # Рисуем символ
        draw.text((x, y), char, fill='black')
        text_x += 50  # Расстояние между символами
    
    # Добавляем шум
    for _ in range(400):
        x = random.randint(0, width-1)
        y = random.randint(0, height-1)
        draw.point((x, y), fill='gray')
    
    # Добавляем линии
    for _ in range(8):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill='gray', width=1)
    
    # Сохраняем в байты
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return captcha_text, img_byte_arr

async def generate_unique_link():
    if not channel_id:
        return "Канал не настроен"
    
    while True:
        link_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        if link_id not in used_links:
            try:
                invite_link = await bot.create_chat_invite_link(
                    chat_id=channel_id,
                    member_limit=1,
                    expire_date=int((datetime.now() + timedelta(hours=24)).timestamp())
                )
                used_links[link_id] = invite_link.invite_link
                return invite_link.invite_link
            except Exception as e:
                print(f"Ошибка при создании ссылки: {e}")
                return "Ошибка при создании ссылки. Пожалуйста, убедитесь, что бот имеет права на создание пригласительных ссылок."

@dp.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR))
async def on_admin_rights_received(event: ChatMemberUpdated):
    global channel_id
    if event.chat.type in ['channel', 'supergroup']:
        channel_id = event.chat.id
        save_settings()
        await bot.send_message(
            chat_id=channel_id,
            text="Капча на канал установлена!"
        )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not channel_id:
        await message.answer("Бот еще не добавлен в канал как администратор. Пожалуйста, добавьте бота в канал и предоставьте права администратора.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Запросить ссылку", callback_data="request_link")]
    ])
    await message.answer("Привет! Нажми на кнопку, чтобы получить ссылку на канал.", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "request_link")
async def process_callback_request_link(callback_query: types.CallbackQuery):
    if not channel_id:
        await callback_query.message.answer("Бот еще не настроен для работы с каналом.")
        await callback_query.answer()
        return

    user_id = callback_query.from_user.id
        
    captcha_text, captcha_image = generate_captcha()
    
    users_data[user_id] = {
        "captcha_text": captcha_text,
        "attempts": 3,
        "timestamp": datetime.now()
    }
    
    await callback_query.message.answer_photo(
        types.BufferedInputFile(captcha_image.getvalue(), filename="captcha.png"),
        caption="Пожалуйста, введите текст с картинки:"
    )
    await callback_query.answer()

@dp.message()
async def check_captcha(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in users_data:
        return
    
    user_data = users_data[user_id]
    
    if datetime.now() - user_data["timestamp"] > timedelta(minutes=5):
        await message.answer("Время сессии истекло. Начните заново с команды /start")
        del users_data[user_id]
        return
    
    if message.text.upper() == user_data["captcha_text"]:
        unique_link = await generate_unique_link()
        await message.answer(f"Поздравляем! Вот ваша одноразовая ссылка на канал:\n{unique_link}")
        del users_data[user_id]
    else:
        user_data["attempts"] -= 1
        if user_data["attempts"] > 0:
            await message.answer(f"Неверный код. Осталось попыток: {user_data['attempts']}")
        else:
            await message.answer("Вы исчерпали все попытки. Начните заново с команды /start")
            del users_data[user_id]

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 