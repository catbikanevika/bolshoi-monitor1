import requests
from bs4 import BeautifulSoup
import hashlib
import os
import sys

def load_seen_ads():
    """Загрузка уже просмотренных объявлений из файла"""
    try:
        with open('seen_ads.txt', 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_seen_ads(seen_ads):
    """Сохранение просмотренных объявлений в файл"""
    with open('seen_ads.txt', 'w') as f:
        for item in seen_ads:
            f.write(item + '\n')

def send_telegram_message(message):
    """Отправка сообщения в Telegram"""
    TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_TOKEN']
    TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print(f"✅ Уведомление отправлено: {message[:50]}...")
            return True
        else:
            print(f"❌ Ошибка Telegram API: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")
        return False

def get_page_content():
    """Получение содержимого страницы"""
    URL = "https://bolshoi.ru/news"
    KEYWORD = "Доступный Большой"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
        print("✅ Страница успешно загружена")
        return response.text, KEYWORD
    except Exception as e:
        print(f"❌ Ошибка загрузки страницы: {e}")
        return None, KEYWORD

def parse_news(html, keyword):
    """Парсинг новостей с сайта"""
    soup = BeautifulSoup(html, 'html.parser')
    news_items = []
    
    # Различные возможные селекторы для новостей
    selectors = [
        '.news-item',
        '.article-item', 
        '.news-list-item',
        '.news-block',
        '[class*="news"]',
        'a[href*="/news/"]',
        'a[href*="/about/press/"]'
    ]
    
    for selector in selectors:
        items = soup.select(selector)
        if items:
            print(f"✅ Найден селектор: {selector}, элементов: {len(items)}")
            
            for item in items:
                # Поиск заголовка
                title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'a']) or item
                title = title_elem.get_text(strip=True)
                
                # Поиск ссылки
                link_elem = item.find('a') or item
                link = link_elem.get('href', '') if hasattr(link_elem, 'get') else ''
                
                if title and len(title) > 10:
                    # Преобразование относительной ссылки в абсолютную
                    if link and link.startswith('/'):
                        link = 'https://bolshoi.ru' + link
                    elif link and not link.startswith('http'):
                        link = 'https://bolshoi.ru' + link
                    
                    # Полный текст для поиска ключевых слов
                    full_text = f"{title} {item.get_text(strip=True)}".lower()
                    
                    news_items.append({
                        'title': title,
                        'link': link,
                        'full_text': full_text,
                        'content': item.get_text(strip=True)
                    })
            break
    
    return news_items

def main():
    """Основная функция"""
    print("🎭 Запуск мониторинга Большого театра через GitHub Actions")
    
    # Загрузка уже просмотренных объявлений
    seen_ads = load_seen_ads()
    print(f"📚 Загружено {len(seen_ads)} просмотренных объявлений")
    
    # Получение контента страницы
    html, keyword = get_page_content()
    
    if not html:
        print("🚨 Не удалось загрузить страницу. Завершение работы.")
        return
    
    # Парсинг новостей
    news_list = parse_news(html, keyword)
    print(f"📰 Найдено элементов на странице: {len(news_list)}")
    
    new_ads_found = False
    
    # Проверка каждой новости
    for news in news_list:
        if keyword.lower() in news['full_text']:
            # Создание уникального хеша для новости
            news_hash = hashlib.md5(f"{news['title']}{news['link']}".encode()).hexdigest()
            
            if news_hash not in seen_ads:
                print(f"🎉 НАЙДЕНА НОВАЯ ЗАПИСЬ: {news['title']}")
                
                # Формирование сообщения для Telegram
                message = (
                    f"🎭 <b>НОВОЕ ОБЪЯВЛЕНИЕ 'Доступный Большой'!</b>\n\n"
                    f"<b>Заголовок:</b> {news['title']}\n"
                )
                
                if news['link']:
                    message += f"<b>Ссылка:</b> {news['link']}\n"
                
                message += f"\n⏰ Обнаружено автоматическим мониторингом"
                
                # Отправка уведомления
                if send_telegram_message(message):
                    seen_ads.add(news_hash)
                    new_ads_found = True
                    print(f"✅ Новое объявление добавлено в историю")
    
    if not new_ads_found:
        print("ℹ️ Новых объявлений с ключевым словом не найдено")
    
    # Сохранение обновленной истории
    save_seen_ads(seen_ads)
    print(f"💾 История сохранена. Всего записей: {len(seen_ads)}")
    
    print("✅ Проверка завершена успешно!")

if __name__ == "__main__":
    main()
