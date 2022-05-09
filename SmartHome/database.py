from tinydb import TinyDB, Query

db = TinyDB('userDb.json')
# db.insert({'rfidTag': '', 'name': 'lisa', 'temperature': 25, 'light': 2900})
# db.insert({'rfidTag': '', 'name': 'ali', 'temperature': 19, 'light': 4000})

for item in db:
    print(item)

RFID = Query()

# db.update({'image': 'aliPP.jpg'}, RFID.name == 'Ali')

# result = db.search(RFID.name == 'Lisa')
# print(result[0]['name'])