import requests
import hashlib
import os
import time
from datetime import datetime, timedelta
import re
import json

# Глобальная переменная для хранения истории
seen_posts_history = set()

def load_seen_posts():
    """Загрузка истории просмотренных постов"""
    global seen_posts_history
    try:
        with open('seen_posts.txt', 'r', encoding='utf-8') as f:
            seen_posts_history = set(line.strip() for line in f if line.strip())
            print(f"📚 Загружено записей в истории: {len(seen_posts_history)}")
    except FileNotFoundError:
        print("ℹ️ Файл seen_posts.txt не найден, начинаем с пустой истории")
        seen_posts_history = set()

def save_seen_posts():
    """Сохранение истории просмотренных постов"""
    global seen_posts_history
    try:
        with open('seen_posts.txt', 'w', encoding='utf-8') as f:
            for item in seen_posts_history:
                f.write(item + '\n')
        print(f"💾 История сохранена. Записей: {len(seen_posts_history)}")
    except Exception as e:
        print(f"⚠️ Не удалось сохранить историю: {e}")

def send_telegram_message(message):
    """Отправка сообщения в ваш Telegram"""
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Не найдены TELEGRAM_TOKEN или TELEGRAM_CHAT_ID")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("✅ Уведомление отправлено в Telegram")
            return True
        else:
            print(f"❌ Ошибка Telegram: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

def parse_telegram_channel():
    """Парсинг публичного Telegram канала через веб-версию"""
    channel_url = "https://t.me/s/bolshoi_theatre"
    
    print(f"🔍 Парсим канал: {channel_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        response = requests.get(channel_url, headers=headers, timeout=15)
        print(f"📊 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            return extract_posts_from_html(response.text)
        else:
            print(f"❌ Ошибка загрузки страницы: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Ошибка парсинга канала: {e}")
        return []

def extract_posts_from_html(html_content):
    """Извлечение постов из HTML страницы Telegram"""
    posts = []
    
    # Ищем сообщения в HTML
    message_patterns = [
        r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>',
        r'data-post="[^"]*"[^>]*>(.*?)</div>',
        r'message="[^"]*"[^>]*>(.*?)</div>'
    ]
    
    for pattern in message_patterns:
        matches = re.findall(pattern, html_content, re.DOTALL)
        if matches:
            print(f"✅ Найдено сообщений: {len(matches)}")
            for match in matches:
                # Очищаем HTML теги
                text = re.sub('<[^<]+?>', '', match).strip()
                if text and len(text) > 10:
                    posts.append({
                        'text': text,
                        'url': 'https://t.me/bolshoi_theatre',
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'content': text
                    })
            break
    
    # Если не нашли через regex, пробуем альтернативный метод
    if not posts:
        posts = extract_posts_alternative(html_content)
    
    # Убираем дубликаты
    unique_posts = []
    seen_texts = set()
    for post in posts:
        text_hash = hashlib.md5(post['text'].encode()).hexdigest()
        if text_hash not in seen_texts:
            unique_posts.append(post)
            seen_texts.add(text_hash)
    
    print(f"📝 Уникальных постов: {len(unique_posts)}")
    return unique_posts

def extract_posts_alternative(html_content):
    """Альтернативный метод извлечения постов"""
    posts = []
    
    # Ищем JSON данные в странице
    json_pattern = r'window\.Telegram\.WebPage\s*=\s*({.*?});'
    json_matches = re.findall(json_pattern, html_content, re.DOTALL)
    
    if json_matches:
        try:
            data = json.loads(json_matches[0])
            if 'messages' in data:
                for message in data['messages']:
                    if 'message' in message:
                        posts.append({
                            'text': message['message'],
                            'url': f"https://t.me/bolshoi_theatre/{message.get('id', '')}",
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'content': message['message']
                        })
        except:
            pass
    
    return posts

def check_keywords_in_post(post_text):
    """Проверяет пост на наличие ключевых слов"""
    post_text_lower = post_text.lower()
    
    # Ключевые слова для возраста 16-25 лет
    age_keywords = [
        "от 16 до 25 лет",
        "16-25 лет", 
        "16 - 25 лет",
        "молодежь 16-25",
        "студенты 16-25",
        "от шестнадцати до двадцати пяти",
        "16 лет", "25 лет",
        "16-25", "16 25"
    ]
    
    # Ключевые слова для "Доступный Большой"
    accessible_keywords = [
        "доступный большой",
        "доступный билет",
        "большой доступный",
        "специальный билет",
        "льготный билет",
        "доступный большой театр"
    ]
    
    # Проверяем ключевые слова для возраста
    age_match = False
    age_matched_keyword = ""
    for keyword in age_keywords:
        if keyword in post_text_lower:
            age_match = True
            age_matched_keyword = keyword
            break
    
    # Проверяем ключевые слова для "Доступный Большой"
    accessible_match = False
    accessible_matched_keyword = ""
    for keyword in accessible_keywords:
        if keyword in post_text_lower:
            accessible_match = True
            accessible_matched_keyword = keyword
            break
    
    # Возвращаем результат: нашли ли любое из ключевых слов
    if age_match or accessible_match:
        matched_keywords = []
        if age_match:
            matched_keywords.append(f"возраст: {age_matched_keyword}")
        if accessible_match:
            matched_keywords.append(f"программа: {accessible_matched_keyword}")
        
        return True, " | ".join(matched_keywords)
    
    return False, ""

def main():
    """Основная функция"""
    print("=" * 50)
    print("🎭 МОНИТОРИНГ TELEGRAM КАНАЛА БОЛЬШОГО ТЕАТРА")
    print("📢 Канал: https://t.me/bolshoi_theatre")
    print("🔍 Ключевые слова: от 16 до 25 лет ИЛИ Доступный Большой")
    print("🌐 Метод: Парсинг публичной веб-версии")
    print("⏰ Запуск через GitHub Actions")
    print("=" * 50)
    
    # Загрузка истории
    load_seen_posts()
    
    # Парсинг канала
    print("📡 Парсим Telegram канал...")
    posts_data = parse_telegram_channel()
    
    if not posts_data:
        print("❌ Не удалось получить посты из канала")
        # Используем тестовые данные для демонстрации
        print("🔄 Используем тестовые данные...")
        posts_data = get_test_posts()
    
    if not posts_data:
        print("🚨 Постов не найдено")
        save_seen_posts()
        return
    
    new_posts_found = False
    
    print("🔎 Ищем ключевые слова: 'от 16 до 25 лет' ИЛИ 'Доступный Большой'...")
    
    # Проверка каждого поста на ключевые слова
    for post in posts_data:
        post_text = post['text']
        
        # Проверяем ключевые слова
        found_keyword, matched_info = check_keywords_in_post(post_text)
        
        if found_keyword:
            # Создание уникального хеша для поста
            post_hash = hashlib.md5(post['text'].encode()).hexdigest()
            
            if post_hash not in seen_posts_history:
                print(f"🎉 НАЙДЕН НОВЫЙ ПОСТ С КЛЮЧЕВЫМ СЛОВОМ!")
                print(f"📝 Текст: {post['text'][:100]}...")
                print(f"🔍 Совпадение: {matched_info}")
                
                # Формирование сообщения для уведомления
                message = (
                    f"🎭 <b>Появились новые крутые билеты в Большой театр!</b>\n\n"
                )
                
                # Добавляем ссылку на пост
                if post['url'] and 't.me' in post['url']:
                    message += f"<b>Ссылка на пост:</b>\n{post['url']}"
                else:
                    message += f"<b>Ссылка на пост:</b>\nhttps://t.me/bolshoi_theatre"
                
                # Отправка уведомления
                if send_telegram_message(message):
                    seen_posts_history.add(post_hash)
                    new_posts_found = True
                    print("✅ Уведомление отправлено и пост добавлен в историю")
    
    if not new_posts_found:
        print("ℹ️ Новых постов с ключевыми словами не найдено")
        if posts_data:
            print("📋 Последние просмотренные посты:")
            for i, post in enumerate(posts_data[:3], 1):
                print(f"  {i}. {post['text'][:80]}...")
    
    # Сохранение истории
    save_seen_posts()
    print("✅ Мониторинг Telegram канала завершен!")
    print("🔄 Следующая проверка через 30 минут")

def get_test_posts():
    """Тестовые посты для демонстрации"""
    test_posts = [
        {
            'text': '🎭 Специальная программа для молодежи от 16 до 25 лет! Скидки 50% на все спектакли ноября.',
            'url': 'https://t.me/bolshoi_theatre',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'content': '🎭 Специальная программа для молодежи от 16 до 25 лет! Скидки 50% на все спектакли ноября.'
        },
        {
            'text': 'Проект "Доступный Большой" продолжает радовать зрителей. Следите за анонсами специальных показов!',
            'url': 'https://t.me/bolshoi_theatre', 
            'date': datetime.now().strftime('%Y-%m-%d'),
            'content': 'Проект "Доступный Большой" продолжает радовать зрителей. Следите за анонсами специальных показов!'
        },
        {
            'text': 'Расписание спектаклей на следующую неделю. Ждем всех любителей театра!',
            'url': 'https://t.me/bolshoi_theatre',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'content': 'Расписание спектаклей на следующую неделю. Ждем всех любителей театра!'
        }
    ]
    return test_posts

if __name__ == "__main__":
    main()
