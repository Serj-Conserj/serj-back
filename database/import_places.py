import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Place, Cuisine, MetroStation
from dotenv import load_dotenv
import os
import uuid
from tqdm import tqdm

load_dotenv()

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('POSTGRES_DB')}"
)

def import_places(json_path: str, db_uri: str):
    engine = create_engine(db_uri)
    Session = sessionmaker(bind=engine, autoflush=False)
    session = Session()
    Base.metadata.create_all(bind=engine)
    try:
        with open(json_path, 'r', encoding='utf-8', errors='replace') as f:
            places_data = json.load(f)

        for idx, place_data in enumerate(places_data):
            if 'full_name' not in place_data or not place_data['full_name']:
                print(f"⚠️ Ошибка в записи #{idx}: Отсутствует full_name")
                print(json.dumps(place_data, indent=2, ensure_ascii=False))
                continue
        
        # Проверка структуры данных
        if not isinstance(places_data, list):
            raise ValueError("Invalid JSON format: expected list of objects")

        BATCH_SIZE = 10
        total = len(places_data)
        
        with tqdm(total=total, desc="Processing places") as pbar:
            for i in range(0, total, BATCH_SIZE):
                batch = places_data[i:i+BATCH_SIZE]
                
                # Проверка и нормализация данных
                validated_batch = []
                for item in batch:
                    if not all(key in item for key in ['full_name', 'main_cuisine', 'close_metro']):
                        print(f"Skipping invalid record: {item.get('full_name')}")
                        continue
                    
                    # Нормализация списков
                    item['main_cuisine'] = item['main_cuisine'] or []
                    item['close_metro'] = item['close_metro'] or []
                    
                    validated_batch.append(item)

                # Пропускаем пустые батчи
                if not validated_batch:
                    pbar.update(len(batch))
                    continue

                # Сбор уникальных значений
                all_cuisines = {c for p in validated_batch for c in p['main_cuisine']}
                all_metros = {m for p in validated_batch for m in p['close_metro']}

                # Создаем кухни
                cuisines_map = {}
                for name in all_cuisines:
                    if not name:  # Пропускаем пустые значения
                        continue
                    cuisine = session.query(Cuisine).filter_by(name=name).first()
                    if not cuisine:
                        cuisine = Cuisine(id=uuid.uuid4(), name=name)
                        session.add(cuisine)
                    cuisines_map[name] = cuisine

                # Создаем метро
                metros_map = {}
                for name in all_metros:
                    if not name:  # Пропускаем пустые значения
                        continue
                    metro = session.query(MetroStation).filter_by(name=name).first()
                    if not metro:
                        metro = MetroStation(id=uuid.uuid4(), name=name)
                        session.add(metro)
                    metros_map[name] = metro

                try:
                    session.flush()
                except Exception as e:
                    session.rollback()
                    print(f"Error during flush: {str(e)}")
                    continue
                success = 0
                errors = 0
                # Добавляем места
                for place_data in validated_batch:
                    try:
                        place = Place(
                            id=uuid.uuid4(),
                            name=str(place_data.get('full_name', '')).strip() or '[Без названия]',
                            alternate_name=place_data.get('alternate_name'),
                            address=place_data.get('address', ''),
                            goo_rating=float(place_data.get('goo_rating', 0)),
                            party_booking_name=place_data.get('party_booking_name', ''),
                            booking_form=place_data.get('booking_form', ''),
                            available_online=False
                        )
                        # session.add(place)
                        
                        # Добавляем связи
                        place.cuisines = [cuisines_map[c] for c in place_data['main_cuisine'] if c in cuisines_map]
                        place.metro_stations = [metros_map[m] for m in place_data['close_metro'] if m in metros_map]
                        success += 1    
                        session.add(place)
                    except Exception as e:
                        errors += 1
                        print(f"🚨 Ошибка в {place_data.get('full_name')}: {str(e)}")
                        session.rollback()
                        print(f"Error creating place {place_data['full_name']}: {str(e)}")
                print(f"Результат: Успешно {success} | Ошибок {errors}")
                try:
                    session.commit()
                    pbar.update(len(validated_batch))
                except Exception as e:
                    session.rollback()
                    print(f"Commit error: {str(e)}")

    except Exception as e:
        print(f"Fatal error: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    import_places(
        json_path='restaurant_data_leclick_1.json',
        db_uri=SQLALCHEMY_DATABASE_URL
    )