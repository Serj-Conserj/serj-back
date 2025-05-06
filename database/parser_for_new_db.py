
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

# Остальные импорты остаются без изменений
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

import json
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
def parse_for_db():
    # Настройки
    URL = 'https://leclick.ru/restaurants/index'
    OUTPUT_FILE = 'database/restaurants.txt'
    MAX_WAIT = 10
    SCROLL_PAUSE = 1

    # Инициализация Firefox с автоматической установкой драйвера
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service)

    # Остальной код остается без изменений
    driver.get(URL)
    restaurant_links = set()

    def scroll_to_bottom():
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE)
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
            last_height = new_height

    try:
        while True:
            WebDriverWait(driver, MAX_WAIT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.image"))
            )
            
            links = driver.find_elements(By.CSS_SELECTOR, 'a.image[href^="/restaurant/"]')
            for link in links:
                href = link.get_attribute('href')
                if href and href not in restaurant_links:
                    restaurant_links.add(href)
                    print(f"Найдено: {href}")
            
            prev_count = len(links)
            scroll_to_bottom()
            
            new_links = driver.find_elements(By.CSS_SELECTOR, 'a.image[href^="/restaurant/"]')
            if len(new_links) == prev_count:
                print("Завершаем сбор данных...")
                break

    except Exception as e:
        print(f"Ошибка: {str(e)}")
    finally:
        driver.quit()

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for link in restaurant_links:
            f.write(f"{link}\n")

    print(f"Собрано {len(restaurant_links)} ссылок. Файл: {OUTPUT_FILE}")





    class RestaurantParser:
        def __init__(self, html, full_url):
            self.soup = BeautifulSoup(html, 'html.parser')
            self.full_url = full_url
            self.base_url = f"{urlparse(full_url).scheme}://{urlparse(full_url).netloc}"

        def get_restaurant_id(self):
            try:
                # Ищем элемент с классом rest-fav-bl и извлекаем data-id
                fav_block = self.soup.find('div', class_='rest-fav-bl')
                if fav_block and fav_block.has_attr('data-id'):
                    return fav_block['data-id']
                
                # Фолбек для старых версий (если потребуется)
                legacy_div = self.soup.find('div', {'data-restaurant-id': True})
                return legacy_div['data-restaurant-id'] if legacy_div else None
                
            except Exception as e:
                print(f"Error getting restaurant id: {str(e)}")
                return None

        def get_names(self):
            names = {
                'main': None,
                'alternate': []
            }
            
            try:
                # 1. Извлечение из URL
                url_path = urlparse(self.full_url).path
                if '/restaurant/' in url_path:
                    slug = unquote(url_path.split('/restaurant/')[-1].split('/')[0])
                    name_from_url = ' '.join(
                        part.capitalize() for part in slug.replace('-', ' ').split()
                    )
                    names['alternate'].append(name_from_url)
                
                # 2. Из data-атрибута
                alternate_name_span = self.soup.find('span', class_='rest-card__fav-icon')
                if alternate_name_span and 'data-name' in alternate_name_span.attrs:
                    names['alternate'].append(alternate_name_span['data-name'].strip())
                
                # 3. Из заголовка
                title_text = self.soup.select_one('.restTitle h1')
                if title_text:
                    title_parts = title_text.text.strip().split('/')
                    names['main'] = title_parts[0].strip()
                    if len(title_parts) > 1:
                        names['alternate'].extend(
                            [p.strip() for p in title_parts[1:] if p.strip()]
                        )
                
                names['alternate'] = list(
                    {name for name in names['alternate'] if name and name != names['main']}
                )
                
            except Exception as e:
                print(f"Error parsing names: {str(e)}")
            
            return names

        def get_phone(self):
            try:
                return self.soup.select_one('.phone-click').text.strip()
            except AttributeError:
                return None

        def get_address(self):
            try:
                return self.soup.select_one('.address .address').text.strip()
            except AttributeError:
                return None

        def get_metro(self):
            try:
                metro_text = self.soup.select_one('.metro').text.strip()
                return [m.strip() for m in metro_text.split(',')]
            except AttributeError:
                return []

        def get_type(self):
            try:
                return self.soup.select_one('.restType').text.strip()
            except AttributeError:
                return None

        def get_average_check(self):
            try:
                check_block = self.soup.find('div', class_='importantInfo').find(
                    'span', string='Средний чек:'
                ).find_parent('div', class_='items')
                
                check_text = check_block.get_text(strip=True).replace('Средний чек:', '')
                
                if '—' in check_text or '-' in check_text:
                    return check_text.replace('—', '-').strip()
                return int(re.sub(r'\D', '', check_text))
            except (AttributeError, ValueError, TypeError):
                return None

        def get_cuisines(self):
            try:
                return [a.text.strip() for a in self.soup.select('.kitchen a')]
            except AttributeError:
                return []

        def get_opening_hours(self):
            hours = {}
            days_map = {
                'd0': 'ВС', 'd1': 'ПН', 'd2': 'ВТ',
                'd3': 'СР', 'd4': 'ЧТ', 'd5': 'ПТ', 'd6': 'СБ'
            }
            
            for day in self.soup.select('[class^="item d"]'):
                class_name = [c for c in day['class'] if c.startswith('d')][0]
                time_from = day.select_one('.timeFrom')
                time_to = day.select_one('.timeTo')
                
                if time_from and time_to:
                    hours[days_map[class_name]] = f"{time_from.text.strip()} - {time_to.text.strip()}"
                else:
                    hours[days_map[class_name]] = 'весь день'
            
            return hours

        def get_menu_links(self):
            menus = {}
            try:
                for link in self.soup.select('.goToMenu'):
                    menu_type = link.text.strip()
                    url = link['href']
                    menus[menu_type] = url
            except AttributeError:
                pass
            return menus

        def get_photos(self):
            # Группируем фото по типам
            photos = {'interior': [], 'food': [], 'facade': []}
            for a in self.soup.select('a[type]'):
                photo_type = a['type']
                if photo_type in photos:
                    photos[photo_type].append(a['href'])
            return photos

        def get_coordinates(self):
            try:
                map_element = self.soup.select_one('.mapAction')
                return {
                    'lat': float(map_element['data-lat']),
                    'lon': float(map_element['data-long'])
                }
            except (AttributeError, KeyError):
                return None

        def get_booking_links(self):
            booking_links = {}
            restraunt_id = self.get_restaurant_id()
            try:
                # Основное бронирование
                main_booking = self.soup.select_one('.bookingBtn.mainBooking a')
                if main_booking:
                    # full_url = urljoin(self.base_url, main_booking['href'])
                    booking_links['main'] = f"https://leclick.ru/restaurants/partner-reserve/id/{restraunt_id}/from/website?lang=ru"

                # Бронирование банкета
                banquet_booking = self.soup.select_one('.bookingBtn a[href*="banquet=1"]')
                if banquet_booking:
                    # full_url = urljoin(self.base_url, banquet_booking['href'])
                    booking_links['banquet'] = f"https://leclick.ru/restaurants/partner-reserve/id/{restraunt_id}/from/website?banquet=1&lang=ru"
            except Exception as e:
                print(f"Error getting booking links: {str(e)}")
            return booking_links

        def get_deposit_rules(self):
            try:
                deposit_rules = self.soup.select_one('.depositRulesText pre').text.strip()
                return deposit_rules.replace('\n', ' ')
            except AttributeError:
                return None

        def get_visit_purposes(self):
            try:
                purpose_block = self.soup.find('div', class_='importantInfo').find(
                    'span', string='Цель посещения:'
                ).find_parent('div', class_='items')
                
                return [a.text.strip() for a in purpose_block.select('a')]
            except AttributeError:
                return []

        def get_features(self):
            try:
                features_block = self.soup.find('div', class_='importantInfo').find(
                    'span', string='Особенности:'
                ).find_parent('div', class_='items')
                
                return [
                    a.text.strip() 
                    for a in features_block.select('a:not(.hidden)')
                    if a.text.strip()
                ]
            except AttributeError:
                return []

        def get_reviews(self):
            reviews = []
            try:
                for review in self.soup.select('.feedback .item'):
                    review_data = {
                        'author': review.select_one('.name').text.strip(),
                        'date': review.select_one('.date').text.strip(),
                        'rating': len(review.select('.material-icons:not(.md-18)')),
                        'text': review.select_one('.review').text.strip() if review.select_one('.review') else None,
                        'source': review.select_one('.partner').text.strip() if review.select_one('.partner') else None
                    }
                    reviews.append(review_data)
            except Exception as e:
                print(f"Error parsing reviews: {str(e)}")
            return reviews

        def parse(self):
            names = self.get_names()
            data = {
                'full_name': names['main'],
                'alternate_name': names['alternate'],
                'phone': self.get_phone(),
                'address': self.get_address(),
                'close_metro': self.get_metro(),
                'type': self.get_type(),
                'average_check': self.get_average_check(),
                'main_cuisine': self.get_cuisines(),
                'opening_hours': self.get_opening_hours(),
                'menu_links': self.get_menu_links(),
                'photos': self.get_photos(),
                'coordinates': self.get_coordinates(),
                'features': {
                    'online_booking': 'принимает' if 'Забронировать' in self.soup.text else 'не принимает'
                },
                'booking_links': self.get_booking_links(),
                'deposit_rules': self.get_deposit_rules(),
                'visit_purposes': self.get_visit_purposes(),
                'features': self.get_features(),
                'reviews': self.get_reviews(),
                'description': self.get_full_description()
            }
            return data

        def get_full_description(self):
            try:
                full_desc = self.soup.select_one('#allDescr')
                if full_desc:
                    return full_desc.text.strip()
                
                short_desc = self.soup.select_one('#shortDescr')
                if short_desc:
                    return short_desc.text.strip()
                
                return self.soup.select_one('.description .text').text.strip()
            except AttributeError:
                return None

    def main():
        start_time = time.time()
        start_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Script started at: {start_dt}")
        
        try:
            with open('database/restaurants.txt', 'r') as f: # restaurants test.txt for test, restaurants.txt for prod
                urls = f.read().splitlines()
            
            results = []
            
            for url in urls:
                try:
                    response = requests.get(url, timeout=15)
                    response.raise_for_status()
                    
                    parser = RestaurantParser(response.text, url)
                    data = parser.parse()
                    
                    data['source'] = {
                        'url': url,
                        'domain': urlparse(url).netloc
                    }
                    
                    results.append(data)
                    
                except Exception as e:
                    print(f"\nError processing {url}: {str(e)}")

            
            with open('database/restaurants.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Fatal error: {str(e)}")
        
        # Тайминг выполнения
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"\nTotal execution time: {elapsed:.2f} seconds")

    
    main()
if __name__ == "__main__":
    parse_for_db()
