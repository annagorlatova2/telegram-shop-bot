import telebot
import sqlite3
import re
from datetime import datetime
from difflib import get_close_matches

BOT_TOKEN = "8813503017:AAHuh0RIJhGEfHn4JSCJaSfrrVoPdmnkSsM"

bot = telebot.TeleBot(BOT_TOKEN)
DB_PATH = "supply_bot.db"

# Для временного хранения данных при редактировании
user_data = {}

def get_db():
    """Подключение к БД"""
    return sqlite3.connect(DB_PATH)

def parse_request(text):
    """
    Парсит заявку формата:
    заявка на 3.09.26  
    школа 2 картошка 21кг морковка 1.5 кг   
    ласточка картошка 8 кг лук 4 кг свекла 3 кг
    """
    lines = text.strip().split('\n')
    
    # Ищем дату
    date_match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2})', lines[0])
    if not date_match:
        return None, "❌ Не найдена дата в формате ДД.МММ.ГГ"
    
    day, month, year = date_match.groups()
    date_str = f"{day.zfill(2)}.{month.zfill(2)}.{year}"
    
    # Парсим строки с контрагентами и товарами
    requests_by_contractor = {}
    current_contractor = None
    
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        
        # Проверяем, может быть это новый контрагент
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name_short FROM contractors")
        contractors = cursor.fetchall()
        conn.close()
        
        # Ищем контрагента по частичному совпадению
        for contractor_id, contractor_name in contractors:
            if contractor_name.lower() in line.lower():
                current_contractor = (contractor_id, contractor_name)
                # Удаляем название контрагента из строки
                line = re.sub(contractor_name, '', line, flags=re.IGNORECASE).strip()
                break
        
        if current_contractor:
            if current_contractor not in requests_by_contractor:
                requests_by_contractor[current_contractor] = []
            
            # Парсим товары: "картошка 21кг" или "картошка 21 кг"
            items = re.findall(r'([\w\s]+?)\s+(\d+(?:,\d+)?)\s*кг', line, re.IGNORECASE)
            for product_search, quantity in items:
                requests_by_contractor[current_contractor].append({
                    'product_search': product_search.strip().lower(),
                    'quantity': float(quantity.replace(',', '.'))
                })
    
    return {
        'date': date_str,
        'requests': requests_by_contractor
    }, None

def find_product(product_search, contractor_id):
    """Находит точное название продукта по частичному совпадению"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Ищем в прайсе контрагента
    cursor.execute("""
        SELECT DISTINCT product_name FROM prices 
        WHERE contractor_id = ?
    """, (contractor_id,))
    
    available_products = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Пытаемся найти по частичному совпадению
    matches = get_close_matches(product_search, available_products, n=1, cutoff=0.6)
    
    if matches:
        return matches[0]
    return None

def get_price(contractor_id, product_name):
    """Получает цену товара для контрагента"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT price FROM prices 
        WHERE contractor_id = ? AND product_name = ?
    """, (contractor_id, product_name))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def get_next_invoice_number():
    """Получает следующий номер счета"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT last_number FROM counters WHERE counter_name = 'invoice_number'")
    result = cursor.fetchone()
    
    if result:
        next_num = result[0] + 1
        cursor.execute("""
            UPDATE counters SET last_number = ? WHERE counter_name = 'invoice_number'
        """, (next_num,))
    else:
        next_num = 1414
        cursor.execute("""
            INSERT INTO counters (counter_name, last_number) VALUES ('invoice_number', ?)
        """, (next_num,))
    
    conn.commit()
    conn.close()
    
    return next_num

def is_potato_only(items):
    """Проверяет, содержит ли список только картофель"""
    return all('картофель' in item['product_search'].lower() for item in items)

def separate_items(items):
    """Разделяет товары на картофель и остальное для ШКОЛА 2"""
    potato_items = []
    other_items = []
    
    for item in items:
        if 'картофель' in item['product_search'].lower():
            potato_items.append(item)
        else:
            other_items.append(item)
    
    return potato_items, other_items

@bot.message_handler(commands=['старт', 'start'])
def start(message):
    text = """👋 Привет! Я бот для работы со счетами и накладными.

📝 Основные команды:
/заявка - отправить заявку на счета
/сверка - акт сверки по контрагенту
/общий_долг - общий долг всех контрагентов
/помощь - полная справка"""
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['помощь', 'help'])
def help_cmd(message):
    text = """📖 **ДОСТУПНЫЕ КОМАНДЫ:**

💼 **ЗАЯВКИ И СЧЕТА:**
/заявка - Отправить заявку на создание счетов

📋 **СВЕРКА:**
/сверка - Акт сверки по контрагенту
/общий_долг - Общий долг всех контрагентов

⚙️ **УПРАВЛЕНИЕ:**
/контрагенты - Список всех контрагентов
/товары - Список всех товаров
/прайс - Прайс контрагента
/добавить_контрагента - Добавить нового контрагента
/добавить_товар - Добавить новый товар для контрагента
/добавить_оплату - Добавить оплату
/изменить_контрагента - Изменить данные контрагента
/список_счетов - Все счета в системе

**ФОРМАТ ЗАЯВКИ:**
```
заявка на 3.09.26
школа 2 картошка 21кг морковка 1.5 кг
ласточка картошка 8 кг лук 4 кг свекла 3 кг
```

**ПРАВИЛА:**
- Школа 2: картошка → счет 1, остальное → счет 2
- Сад 5 + Школа 5: объединяются в одну сверку
- Поиск контрагента по частичному совпадению
- Цены берутся из прайса контрагента"""
    
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['контрагенты'])
def contractors_cmd(message):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name_short, full_name FROM contractors ORDER BY name_short")
    contractors = cursor.fetchall()
    conn.close()
    
    text = "📋 **СПИСОК КОНТРАГЕНТОВ:**\n\n"
    for i, (cid, short, full) in enumerate(contractors, 1):
        text += f"{i}. **{short}** (ID: {cid})\n   {full}\n\n"
    
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['товары'])
def products_cmd(message):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT name FROM products ORDER BY name")
    products = cursor.fetchall()
    conn.close()
    
    text = "📦 **СПИСОК ТОВАРОВ:**\n\n"
    for i, (name,) in enumerate(products, 1):
        text += f"{i}. {name}\n"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['заявка'])
def request_cmd(message):
    text = """📝 Отправьте заявку в следующем формате:

```
заявка на 3.09.26
школа 2 картошка 21кг морковка 1.5 кг
ласточка картошка 8 кг лук 4 кг свекла 3 кг
```

**Обязательно:**
- Первая строка: "заявка на ДД.МММ.ГГ"
- Название контрагента (любая часть)
- Товары с количеством (число+кг)

Я автоматически создам счета и накладные!"""
    
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['список_счетов'])
def list_invoices_cmd(message):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT i.invoice_number, i.date, c.name_short, i.total_amount
        FROM invoices i
        JOIN contractors c ON i.contractor_id = c.id
        ORDER BY i.invoice_number DESC
    """)
    
    invoices = cursor.fetchall()
    conn.close()
    
    text = "📄 **ВСЕ СЧЕТА В СИСТЕМЕ:**\n\n"
    total = 0
    for inv_num, inv_date, contractor, amount in invoices:
        text += f"• №{inv_num} от {inv_date} | {contractor} | {amount:,.2f} руб.\n"
        total += amount
    
    text += f"\n**ВСЕГО: {total:,.2f} руб.**"
    
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['добавить_контрагента'])
def add_contractor_cmd(message):
    msg = bot.reply_to(message, "📝 Введите краткое название контрагента (например: ЛАСТОЧКА)")
    bot.register_next_step_handler(msg, add_contractor_step2)

def add_contractor_step2(message):
    user_id = message.chat.id
    user_data[user_id] = {'name_short': message.text.strip()}
    
    msg = bot.reply_to(message, "📝 Введите полное название контрагента")
    bot.register_next_step_handler(msg, add_contractor_step3)

def add_contractor_step3(message):
    user_id = message.chat.id
    user_data[user_id]['full_name'] = message.text.strip()
    
    msg = bot.reply_to(message, "📝 Введите ИНН")
    bot.register_next_step_handler(msg, add_contractor_step4)

def add_contractor_step4(message):
    user_id = message.chat.id
    user_data[user_id]['inn'] = message.text.strip()
    
    msg = bot.reply_to(message, "📝 Введите КПП")
    bot.register_next_step_handler(msg, add_contractor_step5)

def add_contractor_step5(message):
    user_id = message.chat.id
    user_data[user_id]['kpp'] = message.text.strip()
    
    msg = bot.reply_to(message, "📝 Введите адрес")
    bot.register_next_step_handler(msg, add_contractor_finish)

def add_contractor_finish(message):
    user_id = message.chat.id
    user_data[user_id]['address'] = message.text.strip()
    
    data = user_data[user_id]
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO contractors (name, name_short, full_name, inn, kpp, address, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (data['name_short'].lower(), data['name_short'], data['full_name'], 
              data['inn'], data['kpp'], data['address'], datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ Контрагент {data['name_short']} успешно добавлен!")
        
        del user_data[user_id]
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['добавить_товар'])
def add_product_cmd(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name_short FROM contractors ORDER BY name_short")
    contractors = cursor.fetchall()
    conn.close()
    
    text = "Выберите контрагента:\n"
    for cid, name in contractors:
        text += f"{cid}. {name}\n"
    text += "\nОтправьте ID контрагента"
    
    msg = bot.reply_to(message, text)
    bot.register_next_step_handler(msg, add_product_step2)

def add_product_step2(message):
    user_id = message.chat.id
    try:
        contractor_id = int(message.text.strip())
        user_data[user_id] = {'contractor_id': contractor_id}
        
        msg = bot.reply_to(message, "📝 Введите название товара")
        bot.register_next_step_handler(msg, add_product_step3)
    except:
        bot.reply_to(message, "❌ Неверный ID")

def add_product_step3(message):
    user_id = message.chat.id
    user_data[user_id]['product_name'] = message.text.strip()
    
    msg = bot.reply_to(message, "💰 Введите цену за кг (число с точкой)")
    bot.register_next_step_handler(msg, add_product_finish)

def add_product_finish(message):
    user_id = message.chat.id
    try:
        price = float(message.text.strip())
        data = user_data[user_id]
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Сначала добавляем товар в справочник если его там нет
        cursor.execute("SELECT id FROM products WHERE name = ?", (data['product_name'],))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO products (name, unit, created_at)
                VALUES (?, 'кг', ?)
            """, (data['product_name'], datetime.now().isoformat()))
        
        # Добавляем цену для контрагента
        cursor.execute("""
            INSERT INTO prices (contractor_id, product_name, price, unit, created_at)
            VALUES (?, ?, ?, 'кг', ?)
        """, (data['contractor_id'], data['product_name'], price, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ Товар добавлен! {data['product_name']} - {price} руб/кг")
        del user_data[user_id]
    except:
        bot.reply_to(message, "❌ Ошибка при добавлении цены")

@bot.message_handler(commands=['добавить_оплату'])
def add_payment_cmd(message):
    msg = bot.reply_to(message, """📝 Введите данные оплаты в формате:
номер_счета дата сумма
Например: 1413 10.09.26 12191.00""")
    bot.register_next_step_handler(msg, add_payment_process)

def add_payment_process(message):
    try:
        parts = message.text.strip().split()
        invoice_num = parts[0]
        date_str = parts[1]
        amount = float(parts[2])
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Получаем информацию о счете
        cursor.execute("""
            SELECT contractor_id FROM invoices WHERE invoice_number = ?
        """, (invoice_num,))
        
        result = cursor.fetchone()
        if not result:
            bot.reply_to(message, f"❌ Счет №{invoice_num} не найден")
            conn.close()
            return
        
        contractor_id = result[0]
        
        # Добавляем оплату
        payment_num = f"ОПЛ_{invoice_num}_{date_str}"
        cursor.execute("""
            INSERT INTO payments (payment_number, date, contractor_id, amount, invoice_number, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (payment_num, date_str, contractor_id, amount, invoice_num, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ Оплата добавлена!\n💳 {amount:,.2f} руб. по счету №{invoice_num}")
    except:
        bot.reply_to(message, "❌ Ошибка в формате данных")

@bot.message_handler(commands=['общий_долг'])
def total_debt_cmd(message):
    """Общий долг всех контрагентов"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.name_short, SUM(i.total_amount)
        FROM invoices i
        JOIN contractors c ON i.contractor_id = c.id
        GROUP BY i.contractor_id
        ORDER BY c.name_short
    """)
    
    results = cursor.fetchall()
    conn.close()
    
    text = "💰 **ОБЩИЙ ДОЛГ ВСЕХ КОНТРАГЕНТОВ:**\n\n"
    total = 0
    
    for contractor, amount in results:
        if amount:
            text += f"• {contractor}: {amount:,.2f} руб.\n"
            total += amount
    
    text += f"\n**════════════════════════**\n"
    text += f"**ВСЕГО ДОЛЖНЫ: {total:,.2f} руб.**\n"
    text += f"**════════════════════════**"
    
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['прайс'])
def price_cmd(message):
    text = "Введите название контрагента для просмотра прайса"
    msg = bot.reply_to(message, text)
    bot.register_next_step_handler(msg, show_price)

def show_price(message):
    contractor_search = message.text.strip().lower()
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name_short FROM contractors WHERE name LIKE ? OR name_short LIKE ?",
                 (f"%{contractor_search}%", f"%{contractor_search}%"))
    
    contractor = cursor.fetchone()
    
    if not contractor:
        bot.reply_to(message, f"❌ Контрагент '{contractor_search}' не найден")
        conn.close()
        return
    
    contractor_id, contractor_name = contractor
    
    cursor.execute("""
        SELECT product_name, price FROM prices 
        WHERE contractor_id = ?
        ORDER BY product_name
    """, (contractor_id,))
    
    prices = cursor.fetchall()
    conn.close()
    
    text = f"💵 **ПРАЙС: {contractor_name}**\n\n"
    
    for product, price in prices:
        text += f"• {product}: {price:.2f} руб/кг\n"
    
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: 'заявка на' in message.text.lower())
def process_request(message):
    """Обрабатывает заявку"""
    
    parsed_data, error = parse_request(message.text)
    
    if error:
        bot.reply_to(message, error)
        return
    
    if not parsed_data:
        bot.reply_to(message, "❌ Ошибка при парсировании заявки")
        return
    
    date = parsed_data['date']
    requests = parsed_data['requests']
    
    response = f"📊 **ЗАЯВКА ОТ {date}**\n\n"
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Обрабатываем каждого контрагента
    for (contractor_id, contractor_name), items in requests.items():
        response += f"**{contractor_name}**\n"
        
        # Проверяем, нужна ли разделение на несколько счетов
        is_school2 = 'школа 2' in contractor_name.lower()
        
        if is_school2:
            # ШКОЛА 2 разделяется на 2 счета
            potato_items, other_items = separate_items(items)
            
            # Первый счет - картофель
            if potato_items:
                response += f"  📄 **Счет 1 (Картофель)**:\n"
                total_amount = 0
                invoice_items = []
                
                for item in potato_items:
                    product_name = find_product(item['product_search'], contractor_id)
                    
                    if not product_name:
                        response += f"    ⚠️ Товар '{item['product_search']}' не найден\n"
                        continue
                    
                    price = get_price(contractor_id, product_name)
                    
                    if not price:
                        response += f"    ⚠️ Цена для '{product_name}' не установлена\n"
                        continue
                    
                    quantity = item['quantity']
                    total = quantity * price
                    total_amount += total
                    invoice_items.append((product_name, quantity, price, total))
                    
                    response += f"    ✅ {product_name}: {quantity} кг × {price} = {total:.2f} руб.\n"
                
                if invoice_items:
                    invoice_num = get_next_invoice_number()
                    
                    cursor.execute("""
                        INSERT INTO invoices (invoice_number, date, contractor_id, total_amount, status, created_at)
                        VALUES (?, ?, ?, ?, 'pending', ?)
                    """, (str(invoice_num), date, contractor_id, total_amount, datetime.now().isoformat()))
                    
                    cursor.execute("""
                        INSERT INTO delivery_notes (note_number, date, contractor_id, total_amount, note_type, created_at)
                        VALUES (?, ?, ?, ?, 'main', ?)
                    """, (str(invoice_num), date, contractor_id, total_amount, datetime.now().isoformat()))
                    
                    for product, qty, price, total in invoice_items:
                        cursor.execute("""
                            INSERT INTO note_items (note_number, product_name, quantity, unit, price, total)
                            VALUES (?, ?, ?, 'кг', ?, ?)
                        """, (str(invoice_num), product, qty, price, total))
                    
                    response += f"    📄 Счет №{invoice_num} | {total_amount:.2f} руб.\n\n"
            
            # Второй счет - остальное
            if other_items:
                response += f"  📄 **Счет 2 (Прочие овощи)**:\n"
                total_amount = 0
                invoice_items = []
                
                for item in other_items:
                    product_name = find_product(item['product_search'], contractor_id)
                    
                    if not product_name:
                        response += f"    ⚠️ Товар '{item['product_search']}' не найден\n"
                        continue
                    
                    price = get_price(contractor_id, product_name)
                    
                    if not price:
                        response += f"    ⚠️ Цена для '{product_name}' не установлена\n"
                        continue
                    
                    quantity = item['quantity']
                    total = quantity * price
                    total_amount += total
                    invoice_items.append((product_name, quantity, price, total))
                    
                    response += f"    ✅ {product_name}: {quantity} кг × {price} = {total:.2f} руб.\n"
                
                if invoice_items:
                    invoice_num = get_next_invoice_number()
                    
                    cursor.execute("""
                        INSERT INTO invoices (invoice_number, date, contractor_id, total_amount, status, created_at)
                        VALUES (?, ?, ?, ?, 'pending', ?)
                    """, (str(invoice_num), date, contractor_id, total_amount, datetime.now().isoformat()))
                    
                    cursor.execute("""
                        INSERT INTO delivery_notes (note_number, date, contractor_id, total_amount, note_type, created_at)
                        VALUES (?, ?, ?, ?, 'main', ?)
                    """, (str(invoice_num), date, contractor_id, total_amount, datetime.now().isoformat()))
                    
                    for product, qty, price, total in invoice_items:
                        cursor.execute("""
                            INSERT INTO note_items (note_number, product_name, quantity, unit, price, total)
                            VALUES (?, ?, ?, 'кг', ?, ?)
                        """, (str(invoice_num), product, qty, price, total))
                    
                    response += f"    📄 Счет №{invoice_num} | {total_amount:.2f} руб.\n\n"
        else:
            # Для остальных контрагентов - один счет
            response += f"  📄 **Счет**:\n"
            total_amount = 0
            invoice_items = []
            
            for item in items:
                product_name = find_product(item['product_search'], contractor_id)
                
                if not product_name:
                    response += f"    ⚠️ Товар '{item['product_search']}' не найден\n"
                    continue
                
                price = get_price(contractor_id, product_name)
                
                if not price:
                    response += f"    ⚠️ Цена для '{product_name}' не установлена\n"
                    continue
                
                quantity = item['quantity']
                total = quantity * price
                total_amount += total
                invoice_items.append((product_name, quantity, price, total))
                
                response += f"    ✅ {product_name}: {quantity} кг × {price} = {total:.2f} руб.\n"
            
            if invoice_items:
                invoice_num = get_next_invoice_number()
                
                cursor.execute("""
                    INSERT INTO invoices (invoice_number, date, contractor_id, total_amount, status, created_at)
                    VALUES (?, ?, ?, ?, 'pending', ?)
                """, (str(invoice_num), date, contractor_id, total_amount, datetime.now().isoformat()))
                
                cursor.execute("""
                    INSERT INTO delivery_notes (note_number, date, contractor_id, total_amount, note_type, created_at)
                    VALUES (?, ?, ?, ?, 'main', ?)
                """, (str(invoice_num), date, contractor_id, total_amount, datetime.now().isoformat()))
                
                for product, qty, price, total in invoice_items:
                    cursor.execute("""
                        INSERT INTO note_items (note_number, product_name, quantity, unit, price, total)
                        VALUES (?, ?, ?, 'кг', ?, ?)
                    """, (str(invoice_num), product, qty, price, total))
                
                response += f"    📄 Счет №{invoice_num} | {total_amount:.2f} руб.\n\n"
    
    conn.commit()
    conn.close()
    
    response += "✅ **Заявка обработана!**"
    bot.reply_to(message, response, parse_mode="Markdown")

@bot.message_handler(func=lambda message: 'сверка' in message.text.lower())
def reconcile(message):
    """Обработка команды сверки"""
    parts = message.text.lower().split('сверка')
    if len(parts) < 2:
        bot.reply_to(message, "Укажите название контрагента. Например: /сверка ласточка")
        return
    
    contractor_search = parts[1].strip()
    
    if not contractor_search:
        bot.reply_to(message, "Укажите название контрагента. Например: /сверка ласточка")
        return
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Ищем контрагента
    cursor.execute("""
        SELECT id, name_short FROM contractors 
        WHERE name LIKE ? OR name_short LIKE ?
    """, (f"%{contractor_search}%", f"%{contractor_search}%"))
    
    contractor = cursor.fetchone()
    
    if not contractor:
        bot.reply_to(message, f"❌ Контрагент '{contractor_search}' не найден")
        conn.close()
        return
    
    contractor_id, short_name = contractor
    
    # Получаем счета
    cursor.execute("""
        SELECT invoice_number, date, total_amount FROM invoices
        WHERE contractor_id = ?
        ORDER BY invoice_number DESC
    """, (contractor_id,))
    
    invoices = cursor.fetchall()
    
    text = f"📋 **АКТ СВЕРКИ: {short_name}**\n\n"
    
    if invoices:
        text += "**СЧЕТА:**\n"
        total_invoiced = 0
        for inv_num, inv_date, inv_amount in invoices:
            text += f"  {inv_date} - №{inv_num} - {inv_amount:,.2f} руб.\n"
            total_invoiced += inv_amount
        
        text += f"\n**ИТОГО СЧИСЛЕНО: {total_invoiced:,.2f} руб.**\n"
        
        # Получаем оплаты
        cursor.execute("""
            SELECT date, amount FROM payments
            WHERE contractor_id = ?
            ORDER BY date DESC
        """, (contractor_id,))
        
        payments = cursor.fetchall()
        
        if payments:
            text += "\n**ОПЛАТЫ:**\n"
            total_paid = 0
            for pay_date, pay_amount in payments:
                text += f"  {pay_date} - Поступила: {pay_amount:,.2f} руб.\n"
                total_paid += pay_amount
            
            text += f"\n**ВСЕГО ОПЛАЧЕНО: {total_paid:,.2f} руб.**\n"
        else:
            total_paid = 0
            text += "\n**ОПЛАТ НЕТ**\n"
        
        balance = total_invoiced - total_paid
        text += f"\n**════════════════════**\n"
        if balance > 0:
            text += f"**ЗАДОЛЖЕННОСТЬ: {balance:,.2f} руб.**"
        elif balance < 0:
            text += f"**ПЕРЕПЛАТА: {abs(balance):,.2f} руб.**"
        else:
            text += f"**СВЕРЕНО! ✅**"
        text += f"\n**════════════════════**"
    else:
        text += "Счетов нет"
    
    conn.close()
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "❓ Неизвестная команда. Введите /помощь для справки")

if __name__ == "__main__":
    print("🤖 БОТ ЗАПУЩЕН!")
    print("📊 База данных: supply_bot.db")
    print("💬 Слушаю сообщения в Telegram...")
    print("⚠️  Нажмите Ctrl+C для остановки")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
