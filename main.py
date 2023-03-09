#!/usr/bin/env python3

import json
import urllib.request
import sqlite3
from myconfig import *

print("Retrieving 4 digit location code from myconfig.py file")
try:
    loc
except NameError:
    loc = 2311
    print("No location setting found. Using location: ", loc)
if not str(loc).isdigit() or (int(loc) < 1000) or (int(loc) > 9999):
    loc = 2311
    print("No valid location found! Gathering data for location: ", loc)
else:
    print("Gathering data for location: ", loc)

# req.add_header('Accept', 'application/json, text/javascript, */*; q=0.01')
# req.add_header('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8')
# req.add_header('Origin', 'https://www.thebeerstore.ca')
req = urllib.request.Request(url='https://www.thebeerstore.ca/wp-admin/admin-ajax.php')
req.add_header('Referer', 'https://www.thebeerstore.ca/beers/')
req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:100.0) Gecko/20100101 Firefox/100.0')
req.add_header('Sec-Fetch-Mode', 'cors')
req.add_header('Sec-Fetch-Site', 'same-origin')
req.add_header('TE', 'trailers')

beers = dict()  # Create an empty dictionary to store the relevant data

for page in range(1,25):  # 25 pages (1350 results) should do the trick
    data_str = '&action=beer_filter_ajax&in_stock=on&searchval=&store_id=%s&page_slug=beers&page=%s' % (str(loc), str(page))
    req.data = bytes(data_str, 'utf-8')

    with urllib.request.urlopen(req) as f:
        responseraw = json.loads(f.read())

    if responseraw['pagination']['current_page'] > (final := responseraw['pagination']['total_pages']):
        print(f'Quitting loop after passing page: {final}')
        break

    page = int(responseraw['pagination']['current_page'])
    print("Processing page: ", page)

    # Once in a while, the output is in the form of a list.  
    # In which case we need to transform it into a dictionary 
    # format to work with the rest of the code.

    if type(responseraw['data']) is list:
        response = dict()
        response['data'] = {}
        response['data'] = {i+54*(page-1):responseraw['data'][i] for i in range(len(responseraw['data']))}
        responseraw = response
    
    for i in responseraw['data'].keys():
        current_line = responseraw['data'][i]
        beers[i] = dict()
        beers[i]['id'] = current_line['id']
        beers[i]['name'] = current_line['name'].upper() 
        beers[i]['description'] = current_line['description']
        beers[i]['categories'] = sorted(current_line['categories'])
        for j in current_line['custom_fields']: # Search 'custom_fields' for 'ABV' (alcohol content)
            if j['name'] == 'ABV':
                beers[i]['alcohol'] = float(j['value'])
        beers[i]['variants'] = [] # Create an empty list for the assorted packs
        for j in current_line['variants']:
            if len(j['option_values'][0]['label'].split()) == 5:
                pack, na, ctr, volume, units = j['option_values'][0]['label'].split()
            else:
                pack, na, ctr, volume, units = 1, 'X', 'not_applicable', 1, 'not_applicable'
            # Calculate deposit for bottles, cans and 'other'
            if ctr == 'Bottle':
                deposit = 0.2 if int(volume) > 630 else 0.1
            elif ctr == 'Can':
                deposit = 0.2 if int(volume) > 1000 else 0.1
            else:
                deposit = 0
            # Remove deposit from each pack
            if float(beers[i]['alcohol']) != 0:
                stdBeerPrice = (float(j['sale_price']) - int(pack) * deposit) * 5 * 341 / \
                               int(pack) / int(volume) / float(beers[i]['alcohol'])
            else:
                stdBeerPrice = 100.0 + (float(j['sale_price']) - int(pack) * deposit) * 341 / \
                               int(pack) / int(volume) # Fudged price for the non-alcoholic beers
            beers[i]['variants'].append({'std_beer_price' : round(stdBeerPrice, 3), 'price' : j['price'],
                                         'sale_price' : j['sale_price'], 'inventory' : j['inventory_level'],
                                         'pack' : pack, 'ctr' : ctr, 'volume' : volume, 'units' : units})
            if 'DIS_SKU' in units or 'Keg' in ctr: # Remove discontinued skus and kegs from the collection
                beers[i]['variants'].pop()

        beers[i]['variants'] = sorted(beers[i]['variants'], key=lambda x: (x['ctr'], int(x['volume']), int(x['pack'])))
        beers[i]['cheapest'] = min(list(float(j['std_beer_price']) for j in beers[i]['variants']), default=100)

# Create the SQLite tables and write to them
con = sqlite3.connect("beers.db")
con.execute("DROP TABLE IF EXISTS 'info';")
con.execute("DROP TABLE IF EXISTS 'categories';")
con.execute("DROP TABLE IF EXISTS 'inventory';")
con.commit()
cur = con.cursor()
cur.execute("CREATE TABLE info(id INTEGER PRIMARY KEY, name, description, cheapest, alcohol)")
cur.execute("CREATE TABLE categories(cat_id, category)")
cur.execute("CREATE TABLE inventory(inv_id, std_beer_price, price, sale_price, inventory, pack, ctr, volume, units)")
query_i = "INSERT INTO info VALUES (?,?,?,?,?)"
query_j = "INSERT INTO categories VALUES (?,?)"
query_k = "INSERT INTO inventory VALUES (?,?,?,?,?,?,?,?,?)"
columns_i = ['id', 'name', 'description', 'cheapest', 'alcohol']
columns_k = ['std_beer_price', 'price', 'sale_price', 'inventory', 'pack', 'ctr', 'volume', 'units']
for i in beers.keys():
    keys_i = tuple(beers[i][c] for c in columns_i)
    cur.execute(query_i, keys_i)
    for j in beers[i]['categories']:
        cur.execute(query_j, (beers[i]['id'],j))
    for k in beers[i]['variants']:
        cur.execute(query_k, (beers[i]['id'],) + tuple(k[c] for c in columns_k))

con.commit()
con.execute("VACUUM;")
con.close()

if __name__ == '__main__':
    pass

