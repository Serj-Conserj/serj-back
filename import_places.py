# import json
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from database.models import Base, Place, Cuisine, MetroStation

# # 1. Подключение к БД
# engine = create_engine("postgresql://postgres:123@localhost/main_db")
# Session = sessionmaker(bind=engine)
# db = Session()

# # 2. Создание таблиц (если не созданы через миграции)
# Base.metadata.create_all(bind=engine)

# # 3. Загрузка данных
# def load_data(json_file):
#     with open(json_file, 'r', encoding='utf-8') as f:
#         data = json.load(f)
    
#     for item in data:
#         # Создание ресторана
#         restaurant = Place(
#             name=item['full_name'],
#             alternate_name=item.get('alternate_name'),
#             address=item['address'],
#             goo_rating=float(item['goo_rating']),
#             party_booking_name=item['party_booking_name'],
#             booking_form=item['booking_form']
#         )
#         # print(item.get('main_cuisine', []))
#         if item.get('main_cuisine', []) is None:
#             continue
#         # Обработка кухонь
#         for cuisine_name in item.get('main_cuisine', []):
#             cuisine = db.query(Cuisine).filter(Cuisine.name == cuisine_name).first()
#             if not cuisine:
#                 cuisine = Cuisine(name=cuisine_name)
#                 db.add(cuisine)
#                 db.commit()  # Фиксируем для получения ID
#             restaurant.cuisines.append(cuisine)
        

#         if item.get('close_metro', []) is None:
#             continue
    
#         # Обработка метро
#         for metro_name in item.get('close_metro', []):
#             metro = db.query(MetroStation).filter(MetroStation.name == metro_name).first()
#             if not metro:
#                 metro = MetroStation(name=metro_name)
#                 db.add(metro)
#                 db.commit()  # Фиксируем для получения ID
#             restaurant.metro_stations.append(metro)

     
            
#         db.add(restaurant)
    
#     try:
#         db.commit()
#     except Exception as e:
#         db.rollback()
#         print(f"Ошибка: {e}")
#     finally:
#         db.close()

# if __name__ == "__main__":
#     load_data('restaurant_data_leclick_1.json')


import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Place, Cuisine, MetroStation

def import_places(json_path: str, db_uri: str):
    # Настройка подключения к БД
    engine = create_engine(db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Создание таблиц (если не созданы)
    Base.metadata.create_all(engine)
    
    # Загрузка данных из JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        places_data = json.load(f)
    
    for place_data in places_data:
        # Создание объекта Place
        place = Place(
            name=place_data['full_name'],
            alternate_name=place_data.get('alternate_name'),
            address=place_data['address'],
            goo_rating=float(place_data['goo_rating']),
            party_booking_name=place_data['party_booking_name'],
            booking_form=place_data['booking_form'],
            available_online=False  # Измените, если есть данные в JSON
        )
        
        # Добавление кухонь
        for cuisine_name in place_data['main_cuisine']:
            cuisine = session.query(Cuisine).filter_by(name=cuisine_name).first()
            if not cuisine:
                cuisine = Cuisine(name=cuisine_name)
                session.add(cuisine)
                session.flush()  # Для получения ID
            place.cuisines.append(cuisine)
        
        # Добавление станций метро
        for metro_name in place_data['close_metro']:
            metro = session.query(MetroStation).filter_by(name=metro_name).first()
            if not metro:
                metro = MetroStation(name=metro_name)
                session.add(metro)
                session.flush()
            place.metro_stations.append(metro)
        
        session.add(place)
    
    session.commit()
    session.close()

if __name__ == '__main__':
    import_places(
        json_path='restaurant_data_leclick_1.json',
        db_uri='postgresql://user:password@localhost/dbname'
    )