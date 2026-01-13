import logging
import random
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Берем токен из переменных окружения Render
TOKEN = os.environ.get("TOKEN")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Вместо файла используем словарь (для Render бесплатного тарифа)
USER_DATA = {}

# Символы для слотов
SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍉", "⭐", "7️⃣", "🔔", "💎"]

# Ставки по умолчанию
DEFAULT_BETS = [10, 50, 100, 500, 1000]
BASE_BET = 10

# Получение данных пользователя (в памяти)
def get_user_data(user_id):
    if str(user_id) not in USER_DATA:
        USER_DATA[str(user_id)] = {
            "credits": 1000,
            "games_played": 0,
            "wins": 0,
            "last_spin": None,
            "daily_bonus_claimed": False,
            "current_bet": BASE_BET
        }
    return USER_DATA[str(user_id)]

# Обновление данных пользователя
def update_user_data(user_id, updates):
    if str(user_id) not in USER_DATA:
        get_user_data(user_id)
    
    USER_DATA[str(user_id)].update(updates)

# Генерация слота
def generate_slot_combination():
    return [random.choice(SLOT_SYMBOLS) for _ in range(3)]

# Проверка выигрыша
def check_win(combination):
    if combination[0] == combination[1] == combination[2]:
        if combination[0] == "7️⃣":
            return 50, "ДЖЕКПОТ!!! 🎉"
        elif combination[0] == "💎":
            return 30, "Огромный выигрыш! 💎"
        elif combination[0] == "🔔":
            return 20, "Отличный выигрыш! 🔔"
        else:
            return 10, "Вы выиграли! 🎰"
    
    if combination[0] == combination[1] or combination[1] == combination[2] or combination[0] == combination[2]:
        return 2, "Два одинаковых символа! 👍"
    
    return 0, "Повезет в следующий раз! 😢"

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    keyboard = [
        [InlineKeyboardButton("🎰 Играть в слоты", callback_data="play_slots")],
        [InlineKeyboardButton("💰 Мой баланс", callback_data="balance")],
        [InlineKeyboardButton("⚙️ Изменить ставку", callback_data="change_bet")],
        [InlineKeyboardButton("🎁 Ежедневный бонус", callback_data="daily_bonus")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🎰 *Добро пожаловать в Vegas Slots!* 🎰

💰 *Ваш баланс:* `{user_data['credits']}` кредитов
🎯 *Текущая ставка:* `{user_data.get('current_bet', BASE_BET)}` кредитов

Выберите действие:
    """
    
    await update.message.reply_text(
        text=welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Команда /spin
async def spin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    current_bet = user_data.get('current_bet', BASE_BET)
    
    if user_data["credits"] < current_bet:
        await update.message.reply_text(
            f"❌ *Недостаточно кредитов!*\n\nНужно: `{current_bet}` кредитов\nУ вас: `{user_data['credits']}` кредитов",
            parse_mode='Markdown'
        )
        return
    
    # Вычитаем ставку и обновляем данные
    user_data["credits"] -= current_bet
    user_data["games_played"] += 1
    
    # Генерируем комбинацию и проверяем выигрыш
    combination = generate_slot_combination()
    multiplier, message = check_win(combination)
    win_amount = current_bet * multiplier
    
    if win_amount > 0:
        user_data["credits"] += win_amount
        user_data["wins"] += 1
    
    update_user_data(user_id, {
        "credits": user_data["credits"],
        "games_played": user_data["games_played"],
        "wins": user_data["wins"],
        "last_spin": datetime.now().isoformat()
    })
    
    slot_display = f"| {' | '.join(combination)} |"
    
    result_text = f"""
🎰 *Результат вращения*

{slot_display}

*{message}*

🎯 Ставка: `{current_bet}` кредитов
💰 Выигрыш: `{win_amount}` кредитов
💳 Баланс: `{user_data['credits']}` кредитов
    """
    
    await update.message.reply_text(
        result_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🎰 Крутить еще раз ({current_bet} кредитов)", callback_data="spin_now")],
            [InlineKeyboardButton("⚙️ Изменить ставку", callback_data="change_bet")],
            [InlineKeyboardButton("↩️ В меню", callback_data="back_to_menu")]
        ]),
        parse_mode='Markdown'
    )
    
    if multiplier == 50:
        await update.message.reply_text("🎉 *ДЖЕКПОТ!* 🎉\n*Вы сорвали куш!* 💰", parse_mode='Markdown')

# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if query.data == "play_slots":
        current_bet = user_data.get('current_bet', BASE_BET)
        
        if user_data["credits"] < current_bet:
            await query.edit_message_text(
                text=f"❌ *Недостаточно кредитов!*\n\n💳 Ваш баланс: `{user_data['credits']}`\n🎯 Нужно: `{current_bet}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎁 Получить бонус", callback_data="daily_bonus")],
                    [InlineKeyboardButton("⚙️ Изменить ставку", callback_data="change_bet")],
                    [InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")]
                ]),
                parse_mode='Markdown'
            )
            return
        
        await query.edit_message_text(
            text=f"""
🎰 *Готов к игре!* 🎰

💳 Баланс: `{user_data['credits']}` кредитов
🎯 Ставка: `{current_bet}` кредитов

*Нажмите кнопку ниже чтобы крутить:*
            """,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎰 Крутить за {current_bet} кредитов", callback_data="spin_now")],
                [InlineKeyboardButton("⚙️ Изменить ставку", callback_data="change_bet")],
                [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
                [InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")]
            ]),
            parse_mode='Markdown'
        )
    
    elif query.data == "spin_now":
        await spin_callback(update, context)
    
    elif query.data == "back_to_menu":
        keyboard = [
            [InlineKeyboardButton("🎰 Играть в слоты", callback_data="play_slots")],
            [InlineKeyboardButton("💰 Мой баланс", callback_data="balance")],
            [InlineKeyboardButton("⚙️ Изменить ставку", callback_data="change_bet")],
            [InlineKeyboardButton("🎁 Ежедневный бонус", callback_data="daily_bonus")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
        ]
        await query.edit_message_text(
            text=f"""
🎰 *Главное меню*

💳 Баланс: `{user_data['credits']}` кредитов
🎯 Текущая ставка: `{user_data.get('current_bet', BASE_BET)}` кредитов

*Выберите действие:*
            """,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def spin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    current_bet = user_data.get('current_bet', BASE_BET)
    
    if user_data["credits"] < current_bet:
        await query.answer("❌ Недостаточно кредитов!", show_alert=True)
        return
    
    # Вычитаем ставку
    user_data["credits"] -= current_bet
    user_data["games_played"] += 1
    
    # Генерируем комбинацию
    combination = generate_slot_combination()
    multiplier, message = check_win(combination)
    win_amount = current_bet * multiplier
    
    if win_amount > 0:
        user_data["credits"] += win_amount
        user_data["wins"] += 1
    
    update_user_data(user_id, {
        "credits": user_data["credits"],
        "games_played": user_data["games_played"],
        "wins": user_data["wins"]
    })
    
    slot_display = f"| {' | '.join(combination)} |"
    
    result_text = f"""
🎰 *Результат вращения*

{slot_display}

*{message}*

🎯 Ставка: `{current_bet}` кредитов
💰 Выигрыш: `{win_amount}` кредитов
💳 Баланс: `{user_data['credits']}` кредитов
    """
    
    await query.edit_message_text(
        text=result_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🎰 Крутить еще раз ({current_bet} кредитов)", callback_data="spin_now")],
            [InlineKeyboardButton("⚙️ Изменить ставку", callback_data="change_bet")],
            [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
            [InlineKeyboardButton("↩️ В меню", callback_data="back_to_menu")]
        ]),
        parse_mode='Markdown'
    )

# Главная функция
def main():
    if not TOKEN:
        print("❌ ОШИБКА: Токен не найден!")
        print("ℹ️  Установите переменную окружения TOKEN на Render")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("spin", spin_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🎰 Бот запущен...")
    print("✅ Версия для Render")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# Эта строка ВАЖНА - она запускает бота
if __name__ == "__main__":
    main()
