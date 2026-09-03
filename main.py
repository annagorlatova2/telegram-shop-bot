import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

# Загружаем переменные окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ===== ГЛАВНОЕ МЕНЮ =====
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    """Обработчик команды /start"""
    user_name = message.from_user.first_name
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="📊 Каталог", callback_data="catalog"))
    keyboard.add(InlineKeyboardButton(text="🛒 Корзина", callback_data="cart"))
    keyboard.add(InlineKeyboardButton(text="ℹ️ О нас", callback_data="about"))
    keyboard.add(InlineKeyboardButton(text="📞 Контакты", callback_data="contacts"))
    
    await message.reply(
        f"👋 Привет, {user_name}! 🎉\n\n"
        f"Добро пожаловать в наш магазин! 🛍️\n\n"
        f"Выбери, что тебя интересует:",
        reply_markup=keyboard
    )

# ===== КАТАЛОГ =====
@dp.callback_query_handler(lambda c: c.data == 'catalog')
async def show_catalog(callback_query: types.CallbackQuery):
    """Показываем каталог"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="👕 Футболки", callback_data="category_tshirts"))
    keyboard.add(InlineKeyboardButton(text="👖 Штаны", callback_data="category_pants"))
    keyboard.add(InlineKeyboardButton(text="👟 Кроссовки", callback_data="category_shoes"))
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    
    await callback_query.message.edit_text(
        "📊 Каталог товаров:\n\n"
        "Выбери категорию:",
        reply_markup=keyboard
    )

# ===== КАТЕГОРИЯ: ФУТБОЛКИ =====
@dp.callback_query_handler(lambda c: c.data == 'category_tshirts')
async def show_tshirts(callback_query: types.CallbackQuery):
    """Показываем футболки"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="👕 Футболка красная - 500₽", callback_data="add_red_tshirt"))
    keyboard.add(InlineKeyboardButton(text="👕 Футболка синяя - 500₽", callback_data="add_blue_tshirt"))
    keyboard.add(InlineKeyboardButton(text="👕 Футболка чёрная - 600₽", callback_data="add_black_tshirt"))
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="catalog"))
    
    await callback_query.message.edit_text(
        "👕 Футболки:\n\n"
        "Нажми на товар, чтобы добавить в корзину:",
        reply_markup=keyboard
    )

# ===== КАТЕГОРИЯ: ШТАНЫ =====
@dp.callback_query_handler(lambda c: c.data == 'category_pants')
async def show_pants(callback_query: types.CallbackQuery):
    """Показываем штаны"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="👖 Штаны чёрные - 1500₽", callback_data="add_black_pants"))
    keyboard.add(InlineKeyboardButton(text="👖 Штаны синие - 1500₽", callback_data="add_blue_pants"))
    keyboard.add(InlineKeyboardButton(text="👖 Штаны серые - 1800₽", callback_data="add_gray_pants"))
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="catalog"))
    
    await callback_query.message.edit_text(
        "👖 Штаны:\n\n"
        "Нажми на товар, чтобы добавить в корзину:",
        reply_markup=keyboard
    )

# ===== КАТЕГОРИЯ: КРОССОВКИ =====
@dp.callback_query_handler(lambda c: c.data == 'category_shoes')
async def show_shoes(callback_query: types.CallbackQuery):
    """Показываем кроссовки"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="👟 Кроссовки Nike - 5000₽", callback_data="add_nike_shoes"))
    keyboard.add(InlineKeyboardButton(text="👟 Кроссовки Adidas - 4500₽", callback_data="add_adidas_shoes"))
    keyboard.add(InlineKeyboardButton(text="👟 Кроссовки Puma - 3500₽", callback_data="add_puma_shoes"))
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="catalog"))
    
    await callback_query.message.edit_text(
        "👟 Кроссовки:\n\n"
        "Нажми на товар, чтобы добавить в корзину:",
        reply_markup=keyboard
    )

# ===== ДОБАВЛЕНИЕ В КОРЗИНУ (ФУТБОЛКИ) =====
@dp.callback_query_handler(lambda c: c.data.startswith('add_') and 'tshirt' in c.data)
async def add_tshirt_to_cart(callback_query: types.CallbackQuery):
    """Добавляем футболку в корзину"""
    user_id = callback_query.from_user.id
    
    if callback_query.data == 'add_red_tshirt':
        item = "Футболка красная (500₽)"
    elif callback_query.data == 'add_blue_tshirt':
        item = "Футболка синяя (500₽)"
    else:
        item = "Футболка чёрная (600₽)"
    
    await callback_query.answer(f"✅ {item} добавлена в корзину!", show_alert=True)
    await callback_query.message.edit_text(
        "✅ Товар добавлен в корзину!\n\n"
        "Что дальше?",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton(text="⬅️ Назад в каталог", callback_data="catalog"),
            InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")
        )
    )

# ===== ДОБАВЛЕНИЕ В КОРЗИНУ (ШТАНЫ) =====
@dp.callback_query_handler(lambda c: c.data.startswith('add_') and 'pants' in c.data)
async def add_pants_to_cart(callback_query: types.CallbackQuery):
    """Добавляем штаны в корзину"""
    user_id = callback_query.from_user.id
    
    if callback_query.data == 'add_black_pants':
        item = "Штаны чёрные (1500₽)"
    elif callback_query.data == 'add_blue_pants':
        item = "Штаны синие (1500₽)"
    else:
        item = "Штаны серые (1800₽)"
    
    await callback_query.answer(f"✅ {item} добавлены в корзину!", show_alert=True)
    await callback_query.message.edit_text(
        "✅ Товар добавлен в корзину!\n\n"
        "Что дальше?",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton(text="⬅️ Назад в каталог", callback_data="catalog"),
            InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")
        )
    )

# ===== ДОБАВЛЕНИЕ В КОРЗИНУ (КРОССОВКИ) =====
@dp.callback_query_handler(lambda c: c.data.startswith('add_') and 'shoes' in c.data)
async def add_shoes_to_cart(callback_query: types.CallbackQuery):
    """Добавляем кроссовки в корзину"""
    user_id = callback_query.from_user.id
    
    if callback_query.data == 'add_nike_shoes':
        item = "Кроссовки Nike (5000₽)"
    elif callback_query.data == 'add_adidas_shoes':
        item = "Кроссовки Adidas (4500₽)"
    else:
        item = "Кроссовки Puma (3500₽)"
    
    await callback_query.answer(f"✅ {item} добавлены в корзину!", show_alert=True)
    await callback_query.message.edit_text(
        "✅ Товар добавлен в корзину!\n\n"
        "Что дальше?",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton(text="⬅️ Назад в каталог", callback_data="catalog"),
            InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")
        )
    )

# ===== КОРЗИНА =====
@dp.callback_query_handler(lambda c: c.data == 'cart')
async def show_cart(callback_query: types.CallbackQuery):
    """Показываем корзину"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout"))
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    
    await callback_query.message.edit_text(
        "🛒 Корзина:\n\n"
        "Здесь будут ваши товары\n\n"
        "(В данный момент функция добавления в корзину в разработке)",
        reply_markup=keyboard
    )

# ===== ОФОРМЛЕНИЕ ЗАКАЗА =====
@dp.callback_query_handler(lambda c: c.data == 'checkout')
async def checkout(callback_query: types.CallbackQuery):
    """Оформляем заказ"""
    await callback_query.answer("✅ Спасибо за заказ! Мы скоро свяжемся с вами!", show_alert=True)
    await callback_query.message.edit_text(
        "✅ Заказ принят!\n\n"
        "Благодарим вас за покупку! 🎉\n\n"
        "Мы свяжемся с вами в ближайшее время.",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")
        )
    )

# ===== О НАС =====
@dp.callback_query_handler(lambda c: c.data == 'about')
async def show_about(callback_query: types.CallbackQuery):
    """Показываем информацию о магазине"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    
    await callback_query.message.edit_text(
        "ℹ️ О нас:\n\n"
        "👔 Магазин одежды и обуви\n"
        "📍 Москва, ул. Примерная, 123\n"
        "⭐ Качество гарантировано!\n"
        "🚚 Доставка по всей России\n\n"
        "Спасибо, что выбираете нас! ❤️",
        reply_markup=keyboard
    )

# ===== КОНТАКТЫ =====
@dp.callback_query_handler(lambda c: c.data == 'contacts')
async def show_contacts(callback_query: types.CallbackQuery):
    """Показываем контакты"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    
    await callback_query.message.edit_text(
        "📞 Контакты:\n\n"
        "☎️ Телефон: +7 (999) 123-45-67\n"
        "📧 Email: shop@example.com\n"
        "💬 Telegram: @shopbot\n"
        "🕐 Часы работы: 9:00 - 21:00\n\n"
        "Мы всегда рады помочь! 😊",
        reply_markup=keyboard
    )

# ===== ВЕРНУТЬСЯ В ГЛАВНОЕ МЕНЮ =====
@dp.callback_query_handler(lambda c: c.data == 'back_to_menu')
async def back_to_menu(callback_query: types.CallbackQuery):
    """Возвращаемся в главное меню"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="📊 Каталог", callback_data="catalog"))
    keyboard.add(InlineKeyboardButton(text="🛒 Корзина", callback_data="cart"))
    keyboard.add(InlineKeyboardButton(text="ℹ️ О нас", callback_data="about"))
    keyboard.add(InlineKeyboardButton(text="📞 Контакты", callback_data="contacts"))
    
    await callback_query.message.edit_text(
        "👋 Главное меню\n\n"
        "Выбери, что тебя интересует:",
        reply_markup=keyboard
    )

# ===== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ =====
@dp.message_handler()
async def echo(message: types.Message):
    """Обработчик для остальных сообщений"""
    await message.reply(
        "🤔 Я не понял твою команду...\n\n"
        "Используй /start для перезагрузки меню 👍"
    )

# ===== ЗАПУСК БОТА =====
if __name__ == '__main__':
    print("🤖 Бот запущен!")
    executor.start_polling(dp, skip_updates=True)
