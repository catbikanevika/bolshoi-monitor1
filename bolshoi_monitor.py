import requests
from bs4 import BeautifulSoup
import hashlib
import os
import time
import random

# Глобальная переменная для хранения истории
seen_ads_history = set()

def load_seen_ads():
    """Загрузка истории"""
    global seen_ads_history
    try:
        with open('seen_ads.txt', 'r', encoding='utf-8') as f:
            seen_ads_history = set(line.strip() for line in f if line.strip())
            print(f"📚 Загружено записей в историю: {len(seen_ads_history)}")
    except FileNotFoundError:
        print("ℹ️ Файл seen_ads.txt не найден, начинаем с пустой истории")
        seen_ads_history = set()

def save_seen_ads():
    """Сохранение истории"""
    global seen_ads_history
    try:
        with open('seen_ads.txt', 'w', encoding='utf-8') as f:
            for item in seen_ads_history:
                f.write(item + '\n')
        print(f"💾 История сохранена. Записей: {len(seen_ads_history)}")
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
    """Получение содержимого главной страницы"""
    url = "https://bolshoi.ru/"
    
    # Случайные User-Agent для обхода блокировки
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        print(f"🔗 Пытаемся загрузить: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        print(f"📊 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Главная страница успешно загружена")
            return response.text
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ Таймаут при загрузке страницы")
        return None
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка соединения")
        return None
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return None

def parse_news(html):
    """Парсинг новостей с главной страницы"""
    if not html:
        return []
        
    soup = BeautifulSoup(html, 'html.parser')
    news_items = []
    
    print("🔍 Начинаем поиск новостей на главной странице...")
    
    # Стратегии поиска для главной страницы
    strategies = [
        # Стратегия 1: Поиск по классам, связанным с новостями
        lambda: soup.find_all(class_=lambda x: x and any(word in x.lower() for word in ['news', 'article', 'post', 'item', 'card'])),
        
        # Стратегия 2: Все ссылки с новостями
        lambda: [a for a in soup.find_all('a', href=True) if any(word in a.get('href', '') for word in ['/news/', '/press/', '/about/', '/events/'])],
        
        # Стратегия 3: Заголовки
        lambda: soup.find_all(['h1', 'h2', 'h3', 'h4']),
        
        # Стратегия 4: Все карточки и блоки
        lambda: soup.find_all(['div', 'section', 'article']),
        
        # Стратегия 5: Все ссылки на странице
        lambda: soup.find_all('a', href=True)
    ]
    
    for i, strategy in enumerate(strategies, 1):
        try:
            items = strategy()
            if items:
                print(f"✅ Стратегия {i}: найдено {len(items)} элементов")
                
                for item in items:
                    try:
                        # Получаем заголовок в зависимости от типа элемента
                        if item.name in ['h1', 'h2', 'h3', 'h4']:
                            title = item.get_text(strip=True)
                            # Ищем ссылку рядом с заголовком
                            link_elem = item.find_parent('a') or item.find_next('a')
                            link = link_elem.get('href', '') if link_elem else ''
                        elif item.name == 'a':
                            title = item.get_text(strip=True)
                            link = item.get('href', '')
                        else:
                            title = item.get_text(strip=True)
                            link_elem = item.find('a')
                            link = link_elem.get('href', '') if link_elem else ''
                        
                        # Очистка и проверка заголовка
                        if title and len(title) > 15 and len(title) < 200:
                            # Обработка ссылки
                            if link and link.startswith('/'):
                                link = 'https://bolshoi.ru' + link
                            elif link and not link.startswith('http'):
                                link = 'https://bolshoi.ru/' + link
                            
                            # Пропускаем навигационные и служебные ссылки
                            skip_words = ['вход', 'регистрация', 'поиск', 'english', 'карта', 'расписание', 'купить билет']
                            if any(skip_word in title.lower() for skip_word in skip_words):
                                continue
                                
                            news_items.append({
                                'title': title,
                                'link': link,
                                'content': item.get_text(strip=True)
                            })
                    except Exception as e:
                        continue
                
                if news_items:
                    print(f"🎯 Стратегия {i} успешна! Найдено новостей: {len(news_items)}")
                    break
                    
        except Exception as e:
            print(f"⚠️ Ошибка в стратегии {i}: {e}")
            continue
    
    # Убираем дубликаты по заголовку
    unique_news = []
    seen_titles = set()
    for news in news_items:
        # Нормализуем заголовок для сравнения
        normalized_title = ' '.join(news['title'].lower().split())
        if normalized_title not in seen_titles:
            unique_news.append(news)
            seen_titles.add(normalized_title)
    
    print(f"📰 Уникальных новостей найдено: {len(unique_news)}")
    
    # Покажем первые 3 заголовка для отладки
    if unique_news:
        print("🔍 Примеры найденных заголовков:")
        for i, news in enumerate(unique_news[:3], 1):
            print(f"  {i}. {news['title'][:80]}...")
    
    return unique_news

def main():
    """Основная функция"""
    print("=" * 50)
    print("🎭 МОНИТОРИНГ БОЛЬШОГО ТЕАТРА")
    print("🌐 Главная страница: https://bolshoi.ru/")
    print("⏰ Запуск через GitHub Actions")
    print("=" * 50)
    
    # Загрузка истории
    load_seen_ads()
    
    # Получение страницы
    print("🌐 Загружаем главную страницу...")
    html = get_page_content()
    
    if not html:
        print("🚨 Не удалось загрузить главную страницу")
        return
    
    # Парсинг новостей
    news_list = parse_news(html)
    
    if not news_list:
        print("⚠️ Не удалось найти новости на главной странице")
        return
    
    KEYWORD = "Доступный Большой"
    new_found = False
    
    print(f"🔎 Ищем ключевое слово: '{KEYWORD}'")
    
    # Проверка на ключевое слово
    for news in news_list:
        full_text = f"{news['title']} {news['content']}".lower()
        
        if KEYWORD.lower() in full_text:
            # Создание хеша
            news_hash = hashlib.md5(f"{news['title']}{news['link']}".encode()).hexdigest()
            
            if news_hash not in seen_ads_history:
                print(f"🎉 НАЙДЕНО НОВОЕ ОБЪЯВЛЕНИЕ!")
                print(f"📝 Заголовок: {news['title']}")
                if news['link']:
                    print(f"🔗 Ссылка: {news['link']}")
                
                # Формирование сообщения
                message = (
                    f"🎭 <b>НОВОЕ ОБЪЯВЛЕНИЕ 'Доступный Большой'!</b>\n\n"
                    f"<b>Заголовок:</b>\n{news['title']}\n\n"
                )
                
                if news['link']:
                    message += f"<b>Ссылка:</b>\n{news['link']}\n\n"
                
                message += "🔔 Автоматический мониторинг главной страницы"
                
                # Отправка уведомления
                if send_telegram_message(message):
                    seen_ads_history.add(news_hash)
                    new_found = True
                    print("✅ Уведомление отправлено и добавлено в историю")
    
    if not new_found:
        print("ℹ️ Новых объявлений с ключевым словом не найдено")
        print("📋 Все просмотренные заголовки:")
        for i, news in enumerate(news_list[:10], 1):  # Показываем первые 10
            print(f"  {i}. {news['title'][:70]}...")
    
    # Сохранение истории
    save_seen_ads()
    print("✅ Мониторинг главной страницы завершен!")

if __name__ == "__main__":
    main()
