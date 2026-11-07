import telebot
import requests
from sympy import symbols, solve, sympify, simplify, Eq, integrate, diff, limit

# ТВОЙ ТОКЕН
TOKEN = '9066567820:AAFQ9i7PljI4RAMiWOZ77SnoHTiWsjLRE9s'
HF_API_KEY = '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'
OCR_API_KEY = 'K8180298881425088957'

bot = telebot.TeleBot(TOKEN)

# Сменили модель на более быструю Zephyr
API_URL = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
headers = {"Authorization": f"Bearer {HF_API_KEY}"}

user_histories = {}

# --- МАТЕМАТИЧЕСКИЙ МОДУЛЬ ---
def solve_math(text):
    try:
        text = text.replace('х', 'x').replace('Х', 'X').replace(' ', '').replace('\n', '')
        text = text.replace('÷', '/').replace(',', '.')
        x, y = symbols('x y')
        
        # 1. Пределы
        if text.lower().startswith('limit'):
            expr_text = text[5:].strip('()')
            parts = expr_text.split(',')
            if len(parts) == 3:
                expression = sympify(parts[0])
                var = sympify(parts[1])
                point = sympify(parts[2])
                result = limit(expression, var, point)
                return f"✅ **Предел:** {result}\n📝 **Правило:** Использован предел функции."
        
        # 2. Интегралы
        elif text.lower().startswith('int'):
            expr = sympify(text[3:])
            result = integrate(expr, x)
            return f"✅ **Интеграл:** {result} + C\n📝 **Формула:** ∫ x^n dx = x^(n+1) / (n+1)."
            
        # 3. Производные
        elif text.lower().startswith('diff'):
            expr = sympify(text[4:])
            result = diff(expr, x)
            return f"✅ **Производная:** {result}\n📝 **Формула:** (x^n)' = n * x^(n-1)."
            
        # 4. Системы уравнений
        elif ';' in text:
            equations = text.split(';')
            eqs = []
            for eq in equations:
                if '=' in eq:
                    left, right = eq.split('=')
                    eqs.append(Eq(sympify(left), sympify(right)))
            if eqs:
                solutions = solve(eqs, (x, y), dict=True)
                if not solutions:
                    return "🤔 Система не имеет решений."
                return f"✅ **Решение системы:**\n{solutions}"
                
        # 5. Уравнения
        elif '=' in text:
            left, right = text.split('=')
            eq = Eq(sympify(left), sympify(right))
            expanded = simplify(left - right)
            
            # Если это квадратное уравнение
            if 'x**2' in text and 'x**3' not in text:
                solutions = solve(eq, x)
                if not solutions:
                    return "🤔 Я не нашел решений."
                
                a = expanded.coeff(x, 2)
                b = expanded.coeff(x, 1)
                c = expanded.coeff(x, 0)
                
                answer = "✅ **Корни уравнения:**\n"
                for i, sol in enumerate(solutions, 1):
                    answer += f"x{i} = {sol}\n"
                
                if a != 0:
                    D = b**2 - 4*a*c
                    answer += f"\n📝 **Формула:** ax² + bx + c = 0"
                    answer += f"\nДискриминант D = b² - 4ac = {D}"
                    answer += f"\nx = (-b ± √D) / 2a"
                return answer
            
            # Обычное уравнение
            else:
                solutions = solve(eq, x)
                if not solutions:
                    return "🤔 Я не нашел решений."
                answer = "✅ **Корни уравнения:**\n"
                for i, sol in enumerate(solutions, 1):
                    answer += f"x{i} = {sol}\n"
                return answer

        # 6. Обычные примеры
        else:
            result = sympify(text)
            # Если это просто число (2+2), не пишем про скобки
            if text.isdigit() or ('+' in text and text.replace('+', '').isdigit()):
                 return f"✅ **Ответ:** {simplify(result)}"
            else:
                 return f"✅ **Ответ:** {simplify(result)}\n📝 **Правило:** Порядок действий (умножение/деление, сложение/вычитание)."
            
    except Exception:
        return "❌ Ошибка в примере. Проверь синтаксис. Пиши деление через /"

# --- ФУНКЦИЯ ИИ (ZEPHYR) ---
def ask_ai(user_id, user_text):
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    user_histories[user_id].append({"role": "user", "content": user_text})
    if len(user_histories[user_id]) > 6:
        user_histories[user_id] = user_histories[user_id][-6:]
    
    # Промпт для Zephyr
    prompt = "<|system|>\nТы умный и полезный ассистент. Отвечай на русском языке. Подстраивайся под манеру общения пользователя.</s>\n"
    
    for msg in user_histories[user_id]:
        if msg["role"] == "user":
            prompt += f"<|user|>\n{msg['content']}</s>\n"
        else:
            prompt += f"<|assistant|>\n{msg['content']}</s>\n"
    prompt += "<|assistant|>\n"
            
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 500, "temperature": 0.7, "return_full_text": False}
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            answer = result[0].get('generated_text', '')
            user_histories[user_id].append({"role": "assistant", "content": answer})
            return answer.strip()
        elif isinstance(result, dict) and 'error' in result:
            return f"⏳ Нейросеть перегружена. Напиши еще раз через 10 секунд."
        else:
            return "❌ Ошибка формата ответа."
    except Exception:
        return "❌ Ошибка подключения к ИИ."

# --- ОБРАБОТЧИКИ БОТА ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        "Привет! Я твой умный ИИ-бот. 🧠\n"
        "Я могу общаться на любые темы, а еще решаю математику!\n\n"
        "📌 **Примеры для математики:**\n"
        "• `2+2` \n"
        "• `x**2 - 4 = 0`\n"
        "• `diff x**3`\n"
        "• `int x**2`\n\n"
        "📸 Можешь отправить фото с примером, или просто пиши мне!"
    )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text.strip()
    
    if text.lower().startswith(('int', 'diff', 'limit')) or ('=' in text and 'x' in text) or (text.replace(' ', '').replace('+', '').replace('-', '').replace('*', '').replace('/', '').replace('=', '').replace('?', '').replace('(', '').replace(')', '').isdigit()):
        bot.send_message(message.chat.id, "🧮 Решаю...")
        answer = solve_math(text)
        bot.reply_to(message, answer)
    else:
        bot.send_message(message.chat.id, "🤔 Думаю...")
        answer = ask_ai(message.chat.id, text)
        bot.reply_to(message, answer)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_message(message.chat.id, "📸 Читаю фото, подожди...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        url = 'https://api.ocr.space/parse/image'
        payload = {'apikey': OCR_API_KEY, 'language': 'rus+eng'}
        files = {'file': ('equation.jpg', downloaded_file)}
        
        response = requests.post(url, data=payload, files=files)
        result = response.json()
        
        if result.get('IsErroredOnProcessing'):
            bot.reply_to(message, "❌ Не удалось распознать текст.")
            return
            
        parsed_text = result['ParsedResults'][0]['ParsedText']
        bot.send_message(message.chat.id, f"📝 Я прочитал: `{parsed_text}`", parse_mode='Markdown')
        
        if any(char.isdigit() for char in parsed_text) and ('+' in parsed_text or '-' in parsed_text or '=' in parsed_text or 'x' in parsed_text):
            answer = solve_math(parsed_text)
            bot.reply_to(message, answer)
        else:
            answer = ask_ai(message.chat.id, parsed_text)
            bot.reply_to(message, answer)
            
    except Exception:
        bot.reply_to(message, "❌ Ошибка при обработке фото.")

print("Мульти-Бот запущен...")
bot.polling(none_stop=True)
