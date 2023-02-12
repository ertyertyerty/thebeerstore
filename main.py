import json
import urllib.request
import json2table
import sys

# req.add_header('Accept', 'application/json, text/javascript, */*; q=0.01')
# req.add_header('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8')
# req.add_header('Origin', 'https://www.thebeerstore.ca')

req = urllib.request.Request(url='https://www.thebeerstore.ca/wp-admin/admin-ajax.php')
req.add_header('Referer', 'https://www.thebeerstore.ca/beers/')
req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:100.0) Gecko/20100101 Firefox/100.0')
req.add_header('Sec-Fetch-Mode', 'cors')
req.add_header('Sec-Fetch-Site', 'same-origin')
req.add_header('TE', 'trailers')

beers = dict()

loc = input("Enter your store's 4 digit location code:")
if not loc.isdigit() or (int(loc) < 1000) or (int(loc) > 9999):
    sys.exit("Invalid location code!!")

for page in range(1,25):
    data_str = '&action=beer_filter_ajax&in_stock=on&searchval=&store_id=%s&page_slug=beers&page=%s' % (loc, str(page))
    req.data = bytes(data_str, 'utf-8')

    with urllib.request.urlopen(req) as f:
        responseraw = json.loads(f.read())

    if responseraw['pagination']['current_page'] > (final := responseraw['pagination']['total_pages']):
        print(f'Quitting loop after passing page: {final}')
        break

    page = int(responseraw['pagination']['current_page'])
    print(page)
    #
    # Once in a while, the output is in the form of a list.  In which case we need
    # to transform it into a dictionary format to work with the rest of the code.
    #
    #response = dict()
    #response['data'] = {}
    #response['data'] = {i+54*(page-1):responseraw['data'][i] for i in range(len(responseraw['data']))}
    #print(response['data'].keys())
    #for i in response['data'].keys():
    #print(responseraw['data'].keys())
    for i in responseraw['data'].keys():
        beers[i] = dict()  # Create a blank dictionary to store the selected data
        beers[i]['name'] = responseraw['data'][i]['name'].upper()
        beers[i]['description'] = responseraw['data'][i]['description']
        beers[i]['cheapest'] = 100 # Add the 'cheapest' key here since dict now list items in the order created
        # beers[i]['priciest'] = 100
        # beers[i]['disparity'] = 100
        beers[i]['categories'] = sorted(responseraw['data'][i]['categories'])
        for j in responseraw['data'][i]['custom_fields']:
            if j['name'] == 'ABV':
                beers[i]['alcohol'] = float(j['value'])
        beers[i]['variants'] = [] # Create a blank list for the assorted packs
        for j in responseraw['data'][i]['variants']:
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
            if float(beers[i]['alcohol']) != 0:
                stdBeerPrice = (float(j['sale_price']) - int(pack) * deposit) * 5 * 341 / \
                               int(pack) / int(volume) / float(beers[i]['alcohol'])
            else:
                stdBeerPrice = 100 # Round price for the non-alcoholic beers
            if j['sale_price'] < j['price']:
                j['sale_price'] = '<b>' + str(j['sale_price']) + '</b>'
            beers[i]['variants'].append({'std_beer_price' : round(stdBeerPrice, 3), 'price' : j['price'],
                                         'sale_price' : j['sale_price'], 'inventory' : j['inventory_level'],
                                         'pack' : pack, 'ctr' : ctr, 'volume' : volume, 'units' : units})
            if 'DIS_SKU' in units or 'Keg' in ctr: # Remove discontinued skus and kegs from the collection
                beers[i]['variants'].pop()

        beers[i]['variants'] = sorted(beers[i]['variants'], key=lambda x: (x['ctr'], int(x['volume']), int(x['pack'])))
        beers[i]['cheapest'] = min(list(float(j['std_beer_price']) for j in beers[i]['variants']), default=100)
        # beers[i]['priciest'] = max(list(float(j['std_beer_price']) for j in beers[i]['variants']), default=100)
        # beers[i]['disparity'] = round((beers[i]['priciest'] - beers[i]['cheapest'])/beers[i]['cheapest'], 4)
        #
        # Apply some 'categories' filters
        #
        filters = [162, 164]
        for cat_filter in filters:
            if cat_filter not in beers[i]['categories']:
                del beers[i]
                break
        if i in beers:
            del beers[i]['categories']  # Clean up the output
        # del beers[i]['categories']

ordered = dict(sorted(beers.items(), key=lambda x: x[1]['cheapest'], reverse=False))
outfile = open("beers.html", "w")
build_direction = "LEFT_TO_RIGHT"
# table_attributes = {"style": "width:100%"}
table_attributes = {"style": "text-align:left"}
outfile.write(json2table.convert(ordered, build_direction=build_direction, table_attributes=table_attributes))
outfile.close()

if __name__ == '__main__':
    pass

# categories = [
#     162, # Canada
#     163, # Domestic specialty
#     164, # Mixed case
#     165, 166, 167,
#     168, # Value
#     169, # Lager
#     170, 171, 172, 173,
#     174, # Malt
#     175, 176, 177,
#     178, # Ale
#     179, 180, 181,
#     182, # Pale
#     183, 184,
#     185, # Premium
#     186, # Strong
#     187, 188,
#     189, # Light
#     190, # Flavoured malt
#     191, # Low Calorie
#     192, # Pilsner
#     193, # Non beer
#     194, # Non beer
#     195, # Light
#     196,
#     197, # Fruit
#     198, # Ontario craft
#     199, # India Pale Ale
#     200, # Amber
#     201, # Red
#     202, 203, 204, 205,
#     206, # Lime
#     207, # Low carb
#     208, 209, 210, 211, 212, 213, 214,
#     215, # Stout
#     216, # Dark
#     217, # Blonde
#     218, # Golden
#     219, # Mixed case
#     220, 221,
#     222, # Wheat
#     223,
#     224, # Dry, 225 = Gift Pack?
#     226, # Brown
#     227, # Sessional
#     228, # Honey, 229 = Porter?
#     230, # Cream
#     231, # Seasonal
#     232, # Import
#     234, # Gluten Free
#     235, # Strong
#     236, # Organic
#     237, # Radler
#     238, # Spain
#     239, # United States, 240 = Cider?
#     241, # Belgium
#     242,
#     243, # Germany
#     244, # Trinidad and Tobago
#     245, # United Kingdom
#     246, # Mexico
#     247, # Ireland
#     248, # Turkey
#     249, # Czech Republic
#     250, # Netherlands
#     251, # Denmark
#     252,
#     253, # Singapore
#     254, # Italy
#     255, # France
#     256, # Austria
#     257, # Jamaica, 258 = Greece
#     259, # Poland
#     260, # 261 = China, 262 = Hong Kong, 263 = New Zealand, 264 = Draught
#     265, # Japan, 266 = Costa Rica, 267 = Philippines
#     268,
#     270,
#     271, # 272 = Flavoured
#     275, # What's new
#     276, 278, 280, 281, 283, 284, 285, 286, 287, 298, 299, 300, 301, 303, 309, 311, 314, 315, 319, 321,
#     322, 324, 327, 334, 335, 338, 340, 345, 349, 352, 358, 360, 365, 370, 371, 372, 374, 375, 379, 380,
#     388, 389, 390, 392, 405, 415, 422, 426, 435, 436, 438, 439, 441, 443, 445, 446, 447, 449, 450, 451,
#     452, 453, 454, 455, 456, 457, 458, 459, 461, 467, 469, 471, 473, 474, 477, 478, 494, 497, 498, 504,
#     505, 520, 521, 526, 527, 528, 536, 540
# ]
