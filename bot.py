print("Бот запускается...")

import asyncio
import random
import sqlite3
import time
import re
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8657011541:AAERzvkxXs2ZehbpP0lWO7gwv9BJ7owA8iQ"

# СПИСОК АДМИНОВ
ADMIN_IDS = [7609465565, 5747333526]

def is_admin(user_id):
    return user_id in ADMIN_IDS

# Удаляем старую базу
if os.path.exists("biowar.db"):
    os.remove("biowar.db")
    print("✅ Старая база удалена")

# Новая база
conn = sqlite3.connect('biowar.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    nick TEXT,
    coins INTEGER DEFAULT 0,
    contagion INTEGER DEFAULT 1,
    immunity INTEGER DEFAULT 1,
    infected INTEGER DEFAULT 0,
    sick_count INTEGER DEFAULT 0,
    sick_until REAL DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE cd (
    user_id INTEGER PRIMARY KEY,
    farm REAL DEFAULT 0,
    infect REAL DEFAULT 0
)
''')
conn.commit()
print("✅ База создана")

def get_user(user_id, username, first_name):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    u = cursor.fetchone()
    if not u:
        name = username if username else first_name
        cursor.execute('INSERT INTO users (user_id, username, nick) VALUES (?, ?, ?)', (user_id, username, name))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        u = cursor.fetchone()
    return u

def get_user_by_username(username):
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    return cursor.fetchone()

def get_name(user_id):
    cursor.execute('SELECT nick, username FROM users WHERE user_id = ?', (user_id,))
    r = cursor.fetchone()
    if r and r[0]:
        return r[0]
    if r and r[1]:
        return r[1]
    return "Игрок"

# ========== КОМАНДЫ ==========

async def farm(update: Update, context):
    user = update.effective_user
    u = get_user(user.id, user.username, user.first_name)
    name = get_name(user.id)
    
    cursor.execute('SELECT farm FROM cd WHERE user_id = ?', (user.id,))
    cd = cursor.fetchone()
    if cd and cd[0] and cd[0] > time.time():
        ost = int(cd[0] - time.time())
        await update.message.reply_text(f"⏳ *{name}*, жди {ost//60}мин {ost%60}сек!", parse_mode='Markdown')
        return
    
    reward = random.randint(5, 70)
    new_coins = u[3] + reward
    
    cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, user.id))
    cursor.execute('INSERT INTO cd (user_id, farm) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET farm = excluded.farm', (user.id, time.time() + 3600))
    conn.commit()
    
    await update.message.reply_text(f"🎉 *{name}* +{reward} Е-балов!\n💰 Всего: {new_coins}", parse_mode='Markdown')

async def bag(update: Update, context):
    user = update.effective_user
    u = get_user(user.id, user.username, user.first_name)
    name = get_name(user.id)
    
    await update.message.reply_text(f"🎒 *{name}*\n💰 {u[3]} Е-балов", parse_mode='Markdown')

async def lab(update: Update, context):
    user = update.effective_user
    u = get_user(user.id, user.username, user.first_name)
    name = get_name(user.id)
    
    sick = ""
    if u[8] and u[8] > time.time():
        ost = int(u[8] - time.time())
        sick = f"\n🤒 Болен: {ost//60}мин"
    else:
        sick = "\n🟢 Здоров"
    
    text = f"""🔬 *ЛАБОРАТОРИЯ* 🔬

👤 {name}

🦠 Заразность: {u[4]} ур.
🛡 Иммунитет: {u[5]} ур.
💀 Заразил: {u[6]} раз
😷 Болел: {u[7]} раз
💰 Е-балы: {u[3]}{sick}"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def evolve(update: Update, context):
    user = update.effective_user
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user.id,))
    u = cursor.fetchone()
    name = get_name(user.id)
    
    if u[3] < 15:
        await update.message.reply_text(f"❌ *{name}*, нужно 15 Е-балов! У тебя {u[3]}", parse_mode='Markdown')
        return
    
    new_coins = u[3] - 15
    new_level = u[4] + 1
    
    cursor.execute('UPDATE users SET coins = ?, contagion = ? WHERE user_id = ?', (new_coins, new_level, user.id))
    conn.commit()
    
    await update.message.reply_text(f"🧬 *ЭВОЛЮЦИЯ* 🧬\n\n{name}\nЗаразность: {u[4]} → {new_level}\n💰 -15 Е-балов\n💎 Осталось: {new_coins}", parse_mode='Markdown')

async def vaccine(update: Update, context):
    user = update.effective_user
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user.id,))
    u = cursor.fetchone()
    name = get_name(user.id)
    
    if u[3] < 15:
        await update.message.reply_text(f"❌ *{name}*, нужно 15 Е-балов! У тебя {u[3]}", parse_mode='Markdown')
        return
    
    new_coins = u[3] - 15
    new_level = u[5] + 1
    
    cursor.execute('UPDATE users SET coins = ?, immunity = ? WHERE user_id = ?', (new_coins, new_level, user.id))
    conn.commit()
    
    await update.message.reply_text(f"💉 *ВАКЦИНА* 💉\n\n{name}\nИммунитет: {u[5]} → {new_level}\n💰 -15 Е-балов\n💎 Осталось: {new_coins}", parse_mode='Markdown')

async def set_nick(update: Update, context):
    user = update.effective_user
    text = update.message.text
    
    if not text.startswith('+ник '):
        await update.message.reply_text("❌ Используй: `+ник ТвойНик`", parse_mode='Markdown')
        return
    
    new_nick = text[5:].strip()
    if not new_nick:
        await update.message.reply_text("❌ Напиши ник после +ник", parse_mode='Markdown')
        return
    
    if len(new_nick) > 16:
        await update.message.reply_text(f"❌ Максимум 16 символов! Сейчас {len(new_nick)}", parse_mode='Markdown')
        return
    
    cursor.execute('UPDATE users SET nick = ? WHERE user_id = ?', (new_nick, user.id))
    conn.commit()
    await update.message.reply_text(f"✅ Ник изменён на *{new_nick}*!", parse_mode='Markdown')

async def remove_nick(update: Update, context):
    user = update.effective_user
    cursor.execute('UPDATE users SET nick = NULL WHERE user_id = ?', (user.id,))
    conn.commit()
    await update.message.reply_text(f"✅ Ник сброшен!", parse_mode='Markdown')

# ========== ЗАРАЖЕНИЕ ==========

async def infect(update: Update, context):
    user = update.effective_user
    u = get_user(user.id, user.username, user.first_name)
    name = get_name(user.id)
    
    if u[8] and u[8] > time.time():
        ost = int(u[8] - time.time())
        await update.message.reply_text(f"🦠 *{name}*, ты болен ещё {ost//60}мин! Не можешь заражать.", parse_mode='Markdown')
        return
    
    cursor.execute('SELECT infect FROM cd WHERE user_id = ?', (user.id,))
    cd = cursor.fetchone()
    if cd and cd[0] and cd[0] > time.time():
        ost = int(cd[0] - time.time())
        await update.message.reply_text(f"⏳ КД: {ost}сек", parse_mode='Markdown')
        return
    
    target_id = None
    target_name = None
    target = None
    
    if context.args and len(context.args) > 0:
        target_username = context.args[0].lstrip('@')
        target_data = get_user_by_username(target_username)
        
        if not target_data:
            await update.message.reply_text(f"❌ Пользователь @{target_username} не найден в базе! Попроси его написать любую команду боту.", parse_mode='Markdown')
            return
        
        target_id = target_data[0]
        target_name = get_name(target_id)
        
        if target_id == user.id:
            await update.message.reply_text(f"❌ Нельзя заразить себя!", parse_mode='Markdown')
            return
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (target_id,))
        target = cursor.fetchone()
    
    elif update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = get_name(target_id)
        
        if target_id == user.id:
            await update.message.reply_text(f"❌ Нельзя заразить себя!", parse_mode='Markdown')
            return
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (target_id,))
        target = cursor.fetchone()
        if not target:
            t_user = update.message.reply_to_message.from_user
            target = get_user(target_id, t_user.username, t_user.first_name)
    
    else:
        await update.message.reply_text(f"❌ *{name}*, используй: `заразить @username` или ответь на сообщение!", parse_mode='Markdown')
        return
    
    if target[8] and target[8] > time.time():
        await update.message.reply_text(f"❌ *{target_name}* уже болен!", parse_mode='Markdown')
        return
    
    chance = 80 + (u[4] - target[5]) * 5
    chance = max(30, min(98, chance))
    roll = random.randint(1, 100)
    
    if roll <= chance:
        duration = min(30, 5 + (u[4] // 2)) * 60
        sick_until = time.time() + duration
        reward = random.randint(5, 55)
        
        new_coins = u[3] + reward
        new_infected = u[6] + 1
        new_sick_count = target[7] + 1
        
        cursor.execute('UPDATE users SET coins = ?, infected = ? WHERE user_id = ?', (new_coins, new_infected, user.id))
        cursor.execute('UPDATE users SET sick_until = ?, sick_count = ? WHERE user_id = ?', (sick_until, new_sick_count, target_id))
        cursor.execute('INSERT INTO cd (user_id, infect) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET infect = excluded.infect', (user.id, time.time() + 30))
        conn.commit()
        
        await update.message.reply_text(f"🦠 *{name}* → *{target_name}*\n✅ ЗАРАЖЕНИЕ! Вирус на {duration//60}мин\n💰 +{reward} Е-балов", parse_mode='Markdown')
    else:
        cursor.execute('INSERT INTO cd (user_id, infect) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET infect = excluded.infect', (user.id, time.time() + 30))
        conn.commit()
        await update.message.reply_text(f"🦠 *{name}* → *{target_name}*\n❌ НЕУДАЧА! Иммунитет сработал", parse_mode='Markdown')

async def infect_random(update: Update, context):
    user = update.effective_user
    u = get_user(user.id, user.username, user.first_name)
    name = get_name(user.id)
    
    if u[8] and u[8] > time.time():
        ost = int(u[8] - time.time())
        await update.message.reply_text(f"🦠 *{name}*, ты болен ещё {ost//60}мин! Не можешь заражать.", parse_mode='Markdown')
        return
    
    cursor.execute('SELECT infect FROM cd WHERE user_id = ?', (user.id,))
    cd = cursor.fetchone()
    if cd and cd[0] and cd[0] > time.time():
        ost = int(cd[0] - time.time())
        await update.message.reply_text(f"⏳ КД: {ost}сек", parse_mode='Markdown')
        return
    
    cursor.execute('SELECT user_id FROM users WHERE user_id != ? AND (sick_until IS NULL OR sick_until < ?)', (user.id, time.time()))
    all_users = cursor.fetchall()
    
    if not all_users:
        await update.message.reply_text(f"❌ Нет доступных игроков для заражения!", parse_mode='Markdown')
        return
    
    target = random.choice(all_users)
    target_id = target[0]
    target_name = get_name(target_id)
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (target_id,))
    target = cursor.fetchone()
    
    chance = 80 + (u[4] - target[5]) * 5
    chance = max(30, min(98, chance))
    roll = random.randint(1, 100)
    
    if roll <= chance:
        duration = min(30, 5 + (u[4] // 2)) * 60
        sick_until = time.time() + duration
        reward = random.randint(5, 55)
        
        new_coins = u[3] + reward
        new_infected = u[6] + 1
        new_sick_count = target[7] + 1
        
        cursor.execute('UPDATE users SET coins = ?, infected = ? WHERE user_id = ?', (new_coins, new_infected, user.id))
        cursor.execute('UPDATE users SET sick_until = ?, sick_count = ? WHERE user_id = ?', (sick_until, new_sick_count, target_id))
        cursor.execute('INSERT INTO cd (user_id, infect) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET infect = excluded.infect', (user.id, time.time() + 30))
        conn.commit()
        
        await update.message.reply_text(f"🎲 *{name}* → *{target_name}* (рандом)\n✅ ЗАРАЖЕНИЕ! Вирус на {duration//60}мин\n💰 +{reward} Е-балов", parse_mode='Markdown')
    else:
        cursor.execute('INSERT INTO cd (user_id, infect) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET infect = excluded.infect', (user.id, time.time() + 30))
        conn.commit()
        await update.message.reply_text(f"🎲 *{name}* → *{target_name}* (рандом)\n❌ НЕУДАЧА! Иммунитет сработал", parse_mode='Markdown')

# ========== ТОПЫ ==========

async def top_infected(update: Update, context):
    cursor.execute('SELECT user_id, infected FROM users WHERE infected > 0 ORDER BY infected DESC LIMIT 10')
    top = cursor.fetchall()
    
    if not top:
        await update.message.reply_text("📊 *Нет статистики*", parse_mode='Markdown')
        return
    
    text = "🏆 *ТОП ЗАРАЖЕНИЙ* 🏆\n\n"
    for i, (uid, count) in enumerate(top, 1):
        name = get_name(uid)
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} *{name}* — {count}\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def top_rich(update: Update, context):
    cursor.execute('SELECT user_id, coins FROM users WHERE coins > 0 ORDER BY coins DESC LIMIT 10')
    top = cursor.fetchall()
    
    if not top:
        await update.message.reply_text("💰 *Нет богачей*", parse_mode='Markdown')
        return
    
    text = "💰 *ТОП БОГАЧЕЙ* 💰\n\n"
    for i, (uid, coins) in enumerate(top, 1):
        name = get_name(uid)
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} *{name}* — {coins} Е-балов\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def help_cmd(update: Update, context):
    user = update.effective_user
    get_user(user.id, user.username, user.first_name)
    
    text = """🤖 *BIO WAR БОТ*

📌 *КОМАНДЫ*
`фарма` — получить е-балы (5-70)
`мешок` — баланс
`лаб` — досье
`эволюция` — +заразность (15)
`вакцина` — +иммунитет (15)
`+ник текст` — сменить ник
`-ник` — сбросить ник
`заразить @username` — по юзернейму
`заразить` — ответом на сообщение
`заразить рандом` — случайный игрок
`топ заразы` — топ по заражениям
`топ богатые` — топ по е-балам

🎮 *КД на заражение: 30 секунд*
🦠 *Удачи в BioWar!*"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def start(update: Update, context):
    await help_cmd(update, context)

# ========== АДМИН ==========

async def admin_help(update: Update, context):
    if not is_admin(update.effective_user.id) or update.effective_chat.type != "private":
        return
    text = """👑 *АДМИН-ПАНЕЛЬ* 👑

/give @username число — выдать е-балы
/take @username число — забрать е-балы
/heal @username — вылечить
/sick @username минуты — заразить
/stats — статистика
/userinfo @username — инфо
/list — список игроков
/reset @username — сброс прогресса"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def give(update: Update, context):
    if not is_admin(update.effective_user.id) or update.effective_chat.type != "private":
        return
    if len(context.args) != 2:
        await update.message.reply_text("❌ /give @username число")
        return
    target = context.args[0].lstrip('@')
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Число должно быть цифрами!")
        return
    cursor.execute('SELECT user_id, coins FROM users WHERE username = ?', (target,))
    u = cursor.fetchone()
    if not u:
        await update.message.reply_text(f"❌ @{target} не найден")
        return
    new_coins = u[1] + amount
    cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, u[0]))
    conn.commit()
    await update.message.reply_text(f"✅ Выдано {amount} Е-балов @{target}")

async def take(update: Update, context):
    if not is_admin(update.effective_user.id) or update.effective_chat.type != "private":
        return
    if len(context.args) != 2:
        await update.message.reply_text("❌ /take @username число")
        return
    target = context.args[0].lstrip('@')
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Число должно быть цифрами!")
        return
    cursor.execute('SELECT user_id, coins FROM users WHERE username = ?', (target,))
    u = cursor.fetchone()
    if not u:
        await update.message.reply_text(f"❌ @{target} не найден")
        return
    new_coins = max(0, u[1] - amount)
    cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, u[0]))
    conn.commit()
    await update.message.reply_text(f"✅ Забрано {amount} Е-балов у @{target}")

async def heal(update: Update, context):
    if not is_admin(update.effective_user.id) or update.effective_chat.type != "private":
        return
    if len(context.args) != 1:
        await update.message.reply_text("❌ /heal @username")
        return
    target = context.args[0].lstrip('@')
    cursor.execute('SELECT user_id FROM users WHERE username = ?', (target,))
    u = cursor.fetchone()
    if not u:
        await update.message.reply_text(f"❌ @{target} не найден")
        return
    cursor.execute('UPDATE users SET sick_until = 0 WHERE user_id = ?', (u[0],))
    conn.commit()
    await update.message.reply_text(f"✅ @{target} вылечен")

async def make_sick(update: Update, context):
    if not is_admin(update.effective_user.id) or update.effective_chat.type != "private":
        return
    if len(context.args) != 2:
        await update.message.reply_text("❌ /sick @username минуты")
        return
    target = context.args[0].lstrip('@')
    try:
        minutes = int(context.args[1])
    except:
        await update.message.reply_text("❌ Число должно быть цифрами!")
        return
    cursor.execute('SELECT user_id FROM users WHERE username = ?', (target,))
    u = cursor.fetchone()
    if not u:
        await update.message.reply_text(f"❌ @{target} не найден")
        return
    cursor.execute('UPDATE users SET sick_until = ? WHERE user_id = ?', (time.time() + minutes*60, u[0]))
    conn.commit()
    await update.message.reply_text(f"🦠 @{target} заражён на {minutes} минут")

async def stats(update: Update, context):
    if not is_admin(update.effective_user.id) or update.effective_chat.type != "private":
        return
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT SUM(infected) FROM users')
    infected_sum = cursor.fetchone()[0] or 0
    cursor.execute('SELECT SUM(coins) FROM users')
    coins_sum = cursor.fetchone()[0] or 0
    cursor.execute('SELECT COUNT(*) FROM users WHERE sick_until > ?', (time.time(),))
    sick = cursor.fetchone()[0]
    await update.message.reply_text(f"📊 *СТАТИСТИКА*\n\n👥 Игроков: {total}\n🦠 Заражений: {infected_sum}\n💰 Е-балов: {coins_sum}\n🤒 Больны: {sick}", parse_mode='Markdown')

async def userinfo(update: Update, context):
    if not is_admin(update.effective_user.id) or update.effective_chat.type != "private":
        return
    if len(context.args) != 1:
        await update.message.reply_text("❌ /userinfo @username")
        return
    target = context.args[0].lstrip('@')
    cursor.execute('SELECT * FROM users WHERE username = ?', (target,))
    u = cursor.fetchone()
    if not u:
        await update.message.reply_text(f"❌ @{target} не найден")
        return
    name = u[2] if u[2] else u[1]
    sick_status = "Здоров"
    if u[8] and u[8] > time.time():
        sick_status = f"Болен ({int((u[8]-time.time())//60)}мин)"
    await update.message.reply_text(f"📋 *{name}*\n\n💰 Е-балы: {u[3]}\n🦠 Заразность: {u[4]}\n🛡 Иммунитет: {u[5]}\n💀 Заразил: {u[6]}\n😷 Болел: {u[7]}\n🏥 {sick_status}", parse_mode='Markdown')

async def list_users(update: Update, context):
    if not is_admin(update.effective_user.id) or update.effective_chat.type != "private":
        return
    cursor.execute('SELECT user_id, username, nick, coins, infected FROM users ORDER BY coins DESC LIMIT 20')
    users = cursor.fetchall()
    if not users:
        await update.message.reply_text("📋 Нет игроков")
        return
    text = "📋 *ИГРОКИ*\n\n"
    for i, (uid, username, nick, coins, inf) in enumerate(users, 1):
        name = nick if nick else username
        text += f"{i}. *{name}* — 💰{coins} 🦠{inf}\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def reset(update: Update, context):
    if not is_admin(update.effective_user.id) or update.effective_chat.type != "private":
        return
    if len(context.args) != 1:
        await update.message.reply_text("❌ /reset @username")
        return
    target = context.args[0].lstrip('@')
    cursor.execute('SELECT user_id FROM users WHERE username = ?', (target,))
    u = cursor.fetchone()
    if not u:
        await update.message.reply_text(f"❌ @{target} не найден")
        return
    cursor.execute('UPDATE users SET coins = 0, contagion = 1, immunity = 1, infected = 0, sick_count = 0, sick_until = 0 WHERE user_id = ?', (u[0],))
    cursor.execute('DELETE FROM cd WHERE user_id = ?', (u[0],))
    conn.commit()
    await update.message.reply_text(f"✅ Прогресс @{target} сброшен")

# ========== ЗАПУСК ==========
async def main():
    print("=" * 40)
    print("🤖 БОТ BIO WAR ЗАПУЩЕН!")
    print(f"👑 Админы: {ADMIN_IDS}")
    print("⏱ КД на заражение: 30 секунд")
    print("=" * 40)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Основные команды
    app.add_handler(MessageHandler(filters.Text("фарма"), farm))
    app.add_handler(MessageHandler(filters.Text("мешок"), bag))
    app.add_handler(MessageHandler(filters.Text("лаб"), lab))
    app.add_handler(MessageHandler(filters.Text("эволюция"), evolve))
    app.add_handler(MessageHandler(filters.Text("вакцина"), vaccine))
    app.add_handler(MessageHandler(filters.Regex(r'^заразить\s+@'), infect))
    app.add_handler(MessageHandler(filters.Text("заразить"), infect))
    app.add_handler(MessageHandler(filters.Text("заразить рандом"), infect_random))
    app.add_handler(MessageHandler(filters.Text("топ заразы"), top_infected))
    app.add_handler(MessageHandler(filters.Text("топ богатые"), top_rich))
    app.add_handler(MessageHandler(filters.Text("хелп"), help_cmd))
    app.add_handler(MessageHandler(filters.Text("-ник"), remove_nick))
    app.add_handler(MessageHandler(filters.Regex(r'^\+ник '), set_nick))
    app.add_handler(CommandHandler("start", start))
    
    # Админ команды
    app.add_handler(CommandHandler("admin", admin_help))
    app.add_handler(CommandHandler("give", give))
    app.add_handler(CommandHandler("take", take))
    app.add_handler(CommandHandler("heal", heal))
    app.add_handler(CommandHandler("sick", make_sick))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("userinfo", userinfo))
    app.add_handler(CommandHandler("list", list_users))
    app.add_handler(CommandHandler("reset", reset))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
