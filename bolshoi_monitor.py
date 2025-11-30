import requests
from bs4 import BeautifulSoup
import hashlib
import os

# Глобальная переменная для хранения истории в памяти
seen_ads_history = set()

def load_seen_ads():
    """Загрузка истории - упрощенная версия без коммитов"""
    global seen_ads_history
    try:
        with open('seen_ads.txt', 'r', encoding='utf-8') as f:
            seen_ads_history = set(line.strip() for line in f if line.strip())
            print(f"📚 Загружено записей в историю: {len(seen_ads_history)}")
    except FileNotFoundError:
        print("ℹ️ Файл seen_ads.txt не найден, начинаем с пустой истории")
        seen_ads_history = set()

def save_seen_ads():
    """Сохранение истории - только локально"""
    global seen_ads_history
    try:
        with open('seen_ads.txt', 'w', encoding='utf-8') as f:
            for item in seen_ads_history:
                f.write(item + '\n')
        print(f"💾 История сохранена локально. Записей: {len(seen_ads_history)}")
    except Exception as e:
        print(f"⚠️ Не удалось сохранить историю: {e}")

def send_telegram_message(message):
    """Отправка сообщения в Telegram"""
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

def get_page_content():
    """Получение содержимого страницы"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get('https://bolshoi.ru/news', headers=headers, timeout=15)
        response.raise_for_status()
        print("✅ Страница Большого театра загружена")
        return response.text
    except Exception as e:
        print(f"❌ Ошибка загрузки страницы: {e}")
        return None

def parse_news(html):
    """Парсинг новостей с сайта"""
    soup = BeautifulSoup(html, 'html.parser')
    news_items = []
    
    # Поиск по разным селекторам
    selectors = [
        '.news-item',
        '.article-item', 
        '.news-list-item',
        '[class*="news"]',
        'a[href*="/news/"]',
        'a[href*="/about/press/"]'
    ]
    
    for selector in selectors:
        items = soup.select(selector)
        if items:
            print(f"✅ Найден селектор: {selector} - {len(items)} элементов")
            for item in items:
                # Поиск заголовка
                title_elem = item.find(['h1', 'h2', 'h3', 'h4']) or item.find('a') or item
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # Поиск ссылки
                link_elem = item.find('a') or item
                link = link_elem.get('href', '') if hasattr(link_elem, 'get') else ''
                
                if title and len(title) > 10:
                    # Преобразование относительной ссылки
                    if link and link.startswith('/'):
                        link = 'https://bolshoi.ru' + link
                    elif link and not link.startswith('http'):
                        link = 'https://bolshoi.ru/' + link
                    
                    news_items.append({
                        'title': title,
                        'link': link,
                        'content': item.get_text(strip=True)
                    })
            break
    
    return news_items

def main():
    """Основная функция"""
    print("=" * 50)
    print("🎭 МОНИТОРИНГ БОЛЬШОГО ТЕАТРА")
    print("⏰ Запуск через GitHub Actions")
    print("=" * 50)
    
    # Загрузка истории
    load_seen_ads()
    
    # Получение страницы
    html = get_page_content()
    if not html:
        print("🚨 Завершение работы из-за ошибки загрузки")
        return
    
    # Парсинг новостей
    news_list = parse_news(html)
    print(f"📰 Обработано новостей: {len(news_list)}")
    
    KEYWORD = "Доступный Большой"
    new_found = False
    
    # Проверка на ключевое слово
    for news in news_list:
        full_text = f"{news['title']} {news['content']}".lower()
        
        if KEYWORD.lower() in full_text:
            # Создание хеша
            news_hash = hashlib.md5(f"{news['title']}{news['link']}".encode()).hexdigest()
            
            if news_hash not in seen_ads_history:
                print(f"🎉 НАЙДЕНО НОВОЕ ОБЪЯВЛЕНИЕ!")
                print(f"📝 {news['title']}")
                
                # Формирование сообщения
                message = (
                    f"🎭 <b>НОВОЕ ОБЪЯВЛЕНИЕ 'Доступный Большой'!</b>\n\n"
                    f"<b>Заголовок:</b>\n{news['title']}\n\n"
                )
                
                if news['link']:
                    message += f"<b>Ссылка:</b>\n{news['link']}\n\n"
                
                message += "🔔 Автоматический мониторинг"
                
                # Отправка уведомления
                if send_telegram_message(message):
                    seen_ads_history.add(news_hash)
                    new_found = True
                    print("✅ Уведомление отправлено и добавлено в историю")
    
    if not new_found:
        print("ℹ️ Новых объявлений не найдено")
    
    # Сохранение истории (только локально для этого запуска)
    save_seen_ads()
    print("✅ Мониторинг завершен успешно!")

if __name__ == "__main__":
    main()
