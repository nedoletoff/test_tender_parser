import argparse
import sqlite3
import csv
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def fetch_tenders(max_count: int):
    ''' Функция для получения списка тендеров '''
    base_url = "https://rostender.info/extsearch?page={}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    tenders = []
    page = 1
    collected = 0
    
    while collected < max_count:
        url = base_url.format(page)
        print(f"Обрабатывается страница {page}")
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Ошибка при запросе страницы {page}: {response.status_code}")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Находим все тендеры на странице
            tender_cards = soup.find_all('article', class_='tender-row')
            
            if not tender_cards:
                break  # больше нет тендеров
                
            for card in tender_cards:
                if collected >= max_count:
                    break
                
                try:
                    # Извлекаем ID тендера из атрибута элемента
                    tender_id = card.get('id', '').strip()
                    
                    # Извлекаем название тендера
                    name_tag = card.find('a', class_='tender-info__link')
                    name = name_tag.get_text(strip=True) if name_tag else 'Без названия'
                    
                    # Извлекаем ссылку на тендер
                    relative_link = name_tag['href'] if name_tag else ''
                    link = urljoin('https://rostender.info', relative_link)
                    
                    # Извлекаем заказчика (если доступен)
                    customer_tag = card.find('a', class_='tender__region-link')
                    customer = customer_tag.get_text(strip=True) if customer_tag else 'Не указан'
                    
                    # Извлекаем дату окончания
                    date_span = card.find('span', class_='tender__countdown-text')
                    if date_span:
                        date_part = date_span.find('span', class_='black')
                        time_part = date_span.find('span', class_='tender__countdown-container')
                        if date_part and time_part:
                            end_date = f"{date_part.get_text(strip=True)} {time_part.get_text(strip=True)}"
                        else:
                            end_date = date_span.get_text(strip=True).replace('Окончание (МСК)', '').strip()
                    else:
                        end_date = 'Не указана'
                    
                    tenders.append({
                        'id': tender_id,
                        'name': name,
                        'link': link,
                        'customer': customer,
                        'end_date': end_date
                    })
                    collected += 1
                    
                except Exception as e:
                    print(f"Ошибка при обработке тендера: {e}")
                    continue
            
            page += 1
            
        except Exception as e:
            print(f"Ошибка при запросе страницы {page}: {e}")
            break

    return tenders


def save_to_sqlite(tenders, filename):
    ''' Функция для сохранения списка тендеров в SQLite-базе данных '''
    conn = sqlite3.connect(filename)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tenders
                 (id TEXT, name TEXT, link TEXT, customer TEXT, end_date TEXT)''')

    for tender in tenders:
        c.execute("INSERT INTO tenders VALUES (?,?,?,?,?)",
                  (tender['id'], tender['name'], tender['link'], tender['customer'], tender['end_date']))
    conn.commit()
    conn.close()


def save_to_csv(tenders, filename):
    ''' Функция для сохранения списка тендеров в CSV-файл '''
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'name', 'link', 'customer', 'end_date'])
        writer.writeheader()
        writer.writerows(tenders)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=100, help='Количество тендеров (по умолчанию: 100)')
    parser.add_argument('--output', type=str, default='tenders.db', help='Файл для сохранения (tenders.db или tenders.csv)')
    args = parser.parse_args()

    tenders = fetch_tenders(args.max)

    if args.output.endswith('.csv'):
        save_to_csv(tenders, args.output)
    else:
        save_to_sqlite(tenders, args.output)
    print(f"Сохранено {len(tenders)} тендеров в {args.output}")


if __name__ == '__main__':
    main()
