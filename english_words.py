import json
import sqlite3
import string

def get_db_connection():
    conn = sqlite3.connect('database.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def create_table(first_char):
    conn = get_db_connection()
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {first_char} (
        word TEXT PRIMARY KEY)""")
    conn.commit()
    conn.close()

def insert_into_table(first_char, dict):
    pass

def get_words_json():
    with open('all_english_words.json', 'r') as openfile:
        json_obj = json.load(openfile)
    return json_obj

def update_words_json(dict):
    json_obj = json.dumps(dict, indent = 4)
    with open('english_words_trimmed.json', 'w') as outfile:
        outfile.write(json_obj)

english_words_dict = get_words_json()

new_dict = {word : 0 for word in english_words_dict if len(word) < 8 and len(word) > 4}

alphabets=list(string.ascii_lowercase)

# for char in alphabets:
#     create_table(char)
#     words = []
#     # for word in new_dict:
#         if word[0] == char:
#             words.append(word)
#     json_dict = json.dumps(smol_dict)



update_words_json(new_dict)

# print(len(new_dict))