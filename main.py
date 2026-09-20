import asyncio
import threading
import pystray
from PIL import Image
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ==========================
# ВСТАВЬ СВОЙ ТОКЕН СЮДА
# ==========================
TOKEN = "8888153763:AAG5RtzNWgkpEkOBNiZRju2r6WiVa4NewsU"

# Интервал по умолчанию (минуты)
DEFAULT_MINUTES = 9

# Состояние таймера
timer_minutes = DEFAULT_MINUTES
timer_running = False
timer_task = None


def get_main_keyboard():
    keyboard = [
        ["▶️ Запустить", "⏹ Остановить"],
        ["🔄 Сбросить", "⚙️ Установить время"],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
    )


async def timer_loop(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    global timer_running, timer_minutes

    try:
        while timer_running:
            await asyncio.sleep(timer_minutes * 60)

            if not timer_running:
                break

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔄 Заново",
                        callback_data="restart_timer"
                    ),
                    InlineKeyboardButton(
                        "🗑 Удалить",
                        callback_data="delete_message"
                    ),
                ]
            ])

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"⏰ Таймер завершён\n"
                    f"Продолжительность: {timer_minutes} мин\n\n"
                    f"Пришло время окончания таймера"
                ),
                reply_markup=keyboard,
            )

            # Остановить после окончания
            timer_running = False

    except asyncio.CancelledError:
        pass


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["waiting_for_minutes"] = False

    await update.message.reply_text(
        f"⏰ Таймер готов к работе.\n"
        f"Текущий интервал: {timer_minutes} минут.",
        reply_markup=get_main_keyboard(),
    )


async def keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global timer_running, timer_task, timer_minutes

    text = update.message.text
    chat_id = update.effective_chat.id

    # Запуск
    if text == "▶️ Запустить":
        if timer_running:
            await update.message.reply_text(
                "Таймер уже запущен."
            )
            return

        timer_running = True

        timer_task = context.application.create_task(
            timer_loop(chat_id, context)
        )

        await update.message.reply_text(
            f"▶️ Таймер запущен.\n"
            f"Завершится через {timer_minutes} минут."
        )

    # Остановка
    elif text == "⏹ Остановить":
        if not timer_running:
            await update.message.reply_text(
                "Таймер уже остановлен."
            )
            return

        timer_running = False

        if timer_task:
            timer_task.cancel()
            timer_task = None

        await update.message.reply_text(
            "⏹ Таймер остановлен."
        )

    # Сброс
    elif text == "🔄 Сбросить":
        timer_running = False

        if timer_task:
            timer_task.cancel()
            timer_task = None

        timer_minutes = DEFAULT_MINUTES
        context.user_data["waiting_for_minutes"] = False

        await update.message.reply_text(
            f"🔄 Таймер сброшен.\n"
            f"Интервал снова {DEFAULT_MINUTES} минут."
        )

    # Установка времени
    elif text == "⚙️ Установить время":
        context.user_data["waiting_for_minutes"] = True

        await update.message.reply_text(
            "Введите количество минут.\n\n"
            "Например:\n"
            "15"
        )

    # Ввод нового времени
    elif context.user_data.get("waiting_for_minutes", False):
        try:
            minutes = int(text)

            if minutes <= 0:
                raise ValueError

            timer_minutes = minutes
            context.user_data["waiting_for_minutes"] = False

            await update.message.reply_text(
                f"✅ Новый интервал установлен:\n"
                f"{timer_minutes} минут."
            )

        except ValueError:
            await update.message.reply_text(
                "❌ Введите целое число больше 0."
            )

    else:
        await update.message.reply_text(
            "Нажмите кнопку на панели снизу."
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global timer_running, timer_task

    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id

    # Заново
    if query.data == "restart_timer":
        timer_running = False

        if timer_task:
            timer_task.cancel()

        timer_running = True

        timer_task = context.application.create_task(
            timer_loop(chat_id, context)
        )

        await query.edit_message_text(
            f"▶️ Таймер перезапущен.\n"
            f"Продолжительность: {timer_minutes} минут."
        )

    # Удалить сообщение
    elif query.data == "delete_message":
        await query.message.delete()



# ==========================
# СИСТЕМНЫЙ ТРЕЙ
# ==========================

def exit_app(icon, item):
    global timer_running, timer_task, bot_app
    timer_running = False
    if timer_task:
        timer_task.cancel()
        timer_task = None
    icon.stop()
    if bot_app:
        bot_app.stop_running()


def tray_thread():
    # Создаём простой значок без внешнего файла
    image = Image.new("RGB", (64, 64), "white")
    icon = pystray.Icon(
        "Telegram Timer Bot",
        image,
        "Telegram Timer Bot",
        menu=pystray.Menu(
            pystray.MenuItem("Выход", exit_app)
        )
    )
    icon.run()


bot_app = None


def main():
    global bot_app
    app = Application.builder().token(TOKEN).build()
    bot_app = app

    app.add_handler(CommandHandler("start", start_command))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            keyboard_handler,
        )
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    print("Бот запущен в системном трее...")
    threading.Thread(target=tray_thread, daemon=True).start()
    app.run_polling()


if __name__ == "__main__":
    main()