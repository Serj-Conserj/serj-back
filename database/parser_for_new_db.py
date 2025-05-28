import os
import time
import json
import re
import requests
from datetime import datetime
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from api.utils.logger import logger


def parse_for_db():
    URL = "https://leclick.ru/restaurants/index"
    OUTPUT_FILE = "database/restaurants.txt"
    MAX_WAIT = 10
    SCROLL_PAUSE = 1

    options = Options()
    options.headless = True
    driver = webdriver.Remote(
        command_executor="http://selenium:4444/wd/hub", options=options
    )

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
            links = driver.find_elements(
                By.CSS_SELECTOR, 'a.image[href^="/restaurant/"]'
            )
            for link in links:
                href = link.get_attribute("href")
                if href and href not in restaurant_links:
                    restaurant_links.add(href)
                    logger.info(f"🔗 Найдена ссылка: {href}")

            prev_count = len(links)
            scroll_to_bottom()

            new_links = driver.find_elements(
                By.CSS_SELECTOR, 'a.image[href^="/restaurant/"]'
            )
            if len(new_links) == prev_count:
                logger.info("📦 Завершен сбор всех ссылок")
                break

    except Exception as e:
        logger.error(f"❌ Ошибка при парсинге ссылок: {e}")
    finally:
        driver.quit()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for link in restaurant_links:
            f.write(f"{link}\n")

    logger.info(f"✅ Собрано {len(restaurant_links)} ссылок. Сохранено в {OUTPUT_FILE}")

    class RestaurantParser:
        def __init__(self, html, full_url):
            self.soup = BeautifulSoup(html, "html.parser")
            self.full_url = full_url
            self.base_url = f"{urlparse(full_url).scheme}://{urlparse(full_url).netloc}"

        def get_restaurant_id(self):
            try:
                fav_block = self.soup.find("div", class_="rest-fav-bl")
                if fav_block and fav_block.has_attr("data-id"):
                    return fav_block["data-id"]
                legacy_div = self.soup.find("div", {"data-restaurant-id": True})
                return legacy_div["data-restaurant-id"] if legacy_div else None
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить ID ресторана: {e}")
                return None

        def get_names(self):
            names = {"main": None, "alternate": []}
            try:
                url_path = urlparse(self.full_url).path
                if "/restaurant/" in url_path:
                    slug = unquote(url_path.split("/restaurant/")[-1].split("/")[0])
                    name_from_url = " ".join(
                        part.capitalize() for part in slug.replace("-", " ").split()
                    )
                    names["alternate"].append(name_from_url)

                alternate_name_span = self.soup.find(
                    "span", class_="rest-card__fav-icon"
                )
                if alternate_name_span and "data-name" in alternate_name_span.attrs:
                    names["alternate"].append(alternate_name_span["data-name"].strip())

                title_text = self.soup.select_one(".restTitle h1")
                if title_text:
                    title_parts = title_text.text.strip().split("/")
                    names["main"] = title_parts[0].strip()
                    if len(title_parts) > 1:
                        names["alternate"].extend(
                            [p.strip() for p in title_parts[1:] if p.strip()]
                        )

                names["alternate"] = list(
                    {
                        name
                        for name in names["alternate"]
                        if name and name != names["main"]
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при разборе имен: {e}")
            return names

        def get_phone(self):
            try:
                return self.soup.select_one(".phone-click").text.strip()
            except AttributeError:
                return None

        def get_address(self):
            try:
                return self.soup.select_one(".address .address").text.strip()
            except AttributeError:
                return None

        def get_metro(self):
            try:
                return [
                    m.strip()
                    for m in self.soup.select_one(".metro").text.strip().split(",")
                ]
            except AttributeError:
                return []

        def get_type(self):
            try:
                return self.soup.select_one(".restType").text.strip()
            except AttributeError:
                return None

        def get_average_check(self):
            try:
                check_block = (
                    self.soup.find("div", class_="importantInfo")
                    .find("span", string="Средний чек:")
                    .find_parent("div", class_="items")
                )
                check_text = check_block.get_text(strip=True).replace(
                    "Средний чек:", ""
                )
                if "—" in check_text or "-" in check_text:
                    return check_text.replace("—", "-").strip()
                return int(re.sub(r"\D", "", check_text))
            except (AttributeError, ValueError, TypeError):
                return None

        def get_cuisines(self):
            try:
                return [a.text.strip() for a in self.soup.select(".kitchen a")]
            except AttributeError:
                return []

        def get_opening_hours(self):
            hours = {}
            days_map = {
                "d0": "ВС",
                "d1": "ПН",
                "d2": "ВТ",
                "d3": "СР",
                "d4": "ЧТ",
                "d5": "ПТ",
                "d6": "СБ",
            }
            for day in self.soup.select('[class^="item d"]'):
                class_name = [c for c in day["class"] if c.startswith("d")][0]
                time_from = day.select_one(".timeFrom")
                time_to = day.select_one(".timeTo")
                hours[days_map[class_name]] = (
                    f"{time_from.text.strip()} - {time_to.text.strip()}"
                    if time_from and time_to
                    else "весь день"
                )
            return hours

        def get_menu_links(self):
            menus = {}
            try:
                for link in self.soup.select(".goToMenu"):
                    menu_type = link.text.strip()
                    menus[menu_type] = link["href"]
            except AttributeError:
                pass
            return menus

        def get_photos(self):
            photos = {"interior": [], "food": [], "facade": []}
            for a in self.soup.select("a[type]"):
                photo_type = a["type"]
                if photo_type in photos:
                    photos[photo_type].append(a["href"])
            return photos

        def get_coordinates(self):
            try:
                map_element = self.soup.select_one(".mapAction")
                return {
                    "lat": float(map_element["data-lat"]),
                    "lon": float(map_element["data-long"]),
                }
            except (AttributeError, KeyError):
                return None

        def get_booking_links(self):
            booking_links = {}
            restraunt_id = self.get_restaurant_id()
            try:
                main = self.soup.select_one(".bookingBtn.mainBooking a")
                if main:
                    booking_links["main"] = (
                        f"https://leclick.ru/restaurants/partner-reserve/id/"
                        f"{restraunt_id}/from/website?lang=ru"
                    )
                banquet = self.soup.select_one('.bookingBtn a[href*="banquet=1"]')
                if banquet:
                    booking_links["banquet"] = (
                        f"https://leclick.ru/restaurants/partner-reserve/id/"
                        f"{restraunt_id}/from/website?banquet=1&lang=ru"
                    )
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения ссылок бронирования: {e}")
            return booking_links

        def get_deposit_rules(self):
            try:
                return (
                    self.soup.select_one(".depositRulesText pre")
                    .text.strip()
                    .replace("\n", " ")
                )
            except AttributeError:
                return None

        def get_visit_purposes(self):
            try:
                block = (
                    self.soup.find("div", class_="importantInfo")
                    .find("span", string="Цель посещения:")
                    .find_parent("div", class_="items")
                )
                return [a.text.strip() for a in block.select("a")]
            except AttributeError:
                return []

        def get_features(self):
            try:
                block = (
                    self.soup.find("div", class_="importantInfo")
                    .find("span", string="Особенности:")
                    .find_parent("div", class_="items")
                )
                return [
                    a.text.strip()
                    for a in block.select("a:not(.hidden)")
                    if a.text.strip()
                ]
            except AttributeError:
                return []

        def get_reviews(self):
            reviews = []
            try:
                for review in self.soup.select(".feedback .item"):
                    reviews.append(
                        {
                            "author": review.select_one(".name").text.strip(),
                            "date": review.select_one(".date").text.strip(),
                            "rating": len(review.select(".material-icons:not(.md-18)")),
                            "text": (
                                review.select_one(".review").text.strip()
                                if review.select_one(".review")
                                else None
                            ),
                            "source": (
                                review.select_one(".partner").text.strip()
                                if review.select_one(".partner")
                                else None
                            ),
                        }
                    )
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при разборе отзывов: {e}")
            return reviews

        def get_full_description(self):
            try:
                return (
                    self.soup.select_one("#allDescr")
                    or self.soup.select_one("#shortDescr")
                    or self.soup.select_one(".description .text")
                ).text.strip()
            except AttributeError:
                return None

        def parse(self):
            try:
                names = self.get_names()
                full_name = names.get("main")
                address = self.get_address()

                if not full_name or not address:
                    logger.warning(
                        f"⚠️ Пропуск ресторана: нет имени или адреса — {self.full_url}"
                    )
                    return None

                return {
                    "full_name": full_name,
                    "alternate_name": names.get("alternate", []),
                    "phone": self.get_phone() or None,
                    "address": address,
                    "close_metro": self.get_metro() or [],
                    "type": self.get_type() or None,
                    "average_check": self.get_average_check() or None,
                    "main_cuisine": self.get_cuisines() or [],
                    "opening_hours": self.get_opening_hours() or {},
                    "menu_links": self.get_menu_links() or {},
                    "photos": self.get_photos()
                    or {"interior": [], "food": [], "facade": []},
                    "coordinates": self.get_coordinates() or None,
                    "features": {
                        "online_booking": (
                            "принимает"
                            if "Забронировать" in self.soup.text
                            else "не принимает"
                        )
                    },
                    "booking_links": self.get_booking_links() or {},
                    "deposit_rules": self.get_deposit_rules() or None,
                    "visit_purposes": self.get_visit_purposes() or [],
                    "features": self.get_features() or [],
                    "reviews": self.get_reviews() or [],
                    "description": self.get_full_description() or None,
                }

            except Exception as e:
                logger.warning(f"⚠️ Ошибка при парсинге {self.full_url}: {e}")
                return None

    start_time = time.time()
    logger.info(f"📍 Скрипт запущен в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        with open("database/restaurants.txt", "r") as f:
            urls = f.read().splitlines()

        results = []
        for i, url in enumerate(urls, 1):
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                parser = RestaurantParser(response.text, url)
                data = parser.parse()
                if data is None:
                    logger.warning(f"\n⚠️ Парсинг {url} вернул None")
                    continue
                data["source"] = {"url": url, "domain": urlparse(url).netloc}
                results.append(data)
                print(f". {i}", end="", flush=True)
            except Exception as e:
                logger.warning(f"\n⚠️ Ошибка при обработке {url}: {e}")

        with open("database/restaurants.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"❌ Фатальная ошибка: {e}")

    logger.info(f"⏱️ Время выполнения: {time.time() - start_time:.2f} сек")


if __name__ == "__main__":
    parse_for_db()
