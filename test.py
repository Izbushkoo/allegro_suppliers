import json
import os.path
import time
import uuid

import jwt
import requests
from requests import delete

access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX25hbWUiOiIxMjI2NTc4MDAiLCJzY29wZSI6WyJhbGxlZ3JvOmFwaTpvcmRlcnM6cmVhZCIsImFsbGVncm86YXBpOmZ1bGZpbGxtZW50OnJlYWQiLCJhbGxlZ3JvOmFwaTpwcm9maWxlOndyaXRlIiwiYWxsZWdybzphcGk6c2FsZTpvZmZlcnM6d3JpdGUiLCJhbGxlZ3JvOmFwaTpmdWxmaWxsbWVudDp3cml0ZSIsImFsbGVncm86YXBpOmJpbGxpbmc6cmVhZCIsImFsbGVncm86YXBpOmNhbXBhaWducyIsImFsbGVncm86YXBpOmRpc3B1dGVzIiwiYWxsZWdybzphcGk6c2FsZTpvZmZlcnM6cmVhZCIsImFsbGVncm86YXBpOnNoaXBtZW50czp3cml0ZSIsImFsbGVncm86YXBpOmJpZHMiLCJhbGxlZ3JvOmFwaTpvcmRlcnM6d3JpdGUiLCJhbGxlZ3JvOmFwaTphZHMiLCJhbGxlZ3JvOmFwaTpwYXltZW50czp3cml0ZSIsImFsbGVncm86YXBpOnNhbGU6c2V0dGluZ3M6d3JpdGUiLCJhbGxlZ3JvOmFwaTpwcm9maWxlOnJlYWQiLCJhbGxlZ3JvOmFwaTpyYXRpbmdzIiwiYWxsZWdybzphcGk6c2FsZTpzZXR0aW5nczpyZWFkIiwiYWxsZWdybzphcGk6cGF5bWVudHM6cmVhZCIsImFsbGVncm86YXBpOnNoaXBtZW50czpyZWFkIiwiYWxsZWdybzphcGk6bWVzc2FnaW5nIl0sImFsbGVncm9fYXBpIjp0cnVlLCJpc3MiOiJodHRwczovL2FsbGVncm8ucGwiLCJleHAiOjE3MzM5NjE2MDAsImp0aSI6IjBlZDJmMDEwLWI4MDctNDZjZi04ZDM4LWZmNjE3NzI3ZDRmYyIsImNsaWVudF9pZCI6ImJkZDRkYTA1MThkOTQ5YzRiMDkxYTZhYmU0ZmQ4M2Y3In0.OiVg-TgIb28IjL4EW2n2sRk-_7wwVHP7TN9dkpO4RyKWBoOL9P-LsFKUHDvLnvzZbhtW0oHUyOnq1liTqJ4-AAPjY51oD1T0cqLb5DAhe1Bwmc2BDIR9fisoe5dMC9YCYwe9kGFb8ovK1R5Lp6AfUDLA6a8wq2lOJXkRXRaoTfh-B_d5f0ZDHfECajaz40CiKSvplqwWix2-G_UzCjNw-RRPJfAIWZp5FkFU2rGTVuziKG2iDAOrj3TmYja98ZZfC7cRfwzBFit947BQAjxO5pHDXS3l-U2PyxzIcOf_TtkGIse9lEntk8UKWEKg9d2oBc9Az4nW34xc0Lno6j-qPg"


headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/vnd.allegro.public.v1+json",
    "Accept": "application/vnd.allegro.public.v1+json",
}


def get_offers(limit=900, offset=0):

    params = {
        "limit": limit,
        "offset": offset
    }

    url = f"https://api.allegro.pl/sale/offers"

    response = requests.get(url, headers=headers, params=params)
    # response.raise_for_status()
    resp = response.json()

    # with open("products.json", "w") as file:
    #     file.write(json.dumps(resp, indent=4))

    # print(len(response.json()["offers"]))
    return resp


def get_all_offers_filter(supplier_prefix: str):

    current = 0
    batch = 900
    total = get_offers(limit=1)["totalCount"]

    offers = []
    while current < total:
        batch_offers = get_offers(limit=batch, offset=current)
        print(batch_offers["offers"][0])
        filtered = []
        for offer in batch_offers["offers"]:
            if offer["external"]:
                if offer["external"]['id'] and offer["external"]['id'].startswith(supplier_prefix):
                    filtered.append(offer)
            else:
                print(offer)

        offers += filtered
        current += batch_offers["count"]

    with open("all_filtered_offers.json", "w") as file:
        file.write(json.dumps(offers, indent=4))

    print(len(offers))
    return offers


exclude_ = ["15193904908", "15221979431", "15221893453", "15226795111", "15152356217", "15156052034", "15134639326",
            "15142137283", "15112772370", "15226872005", "15163112735", "15226918914", "15226937696", "15141963766",
            "16246163234", "16248412238", "15512762792", "15496129185", "15495863511", "15280815954", "15280626256",
            "15280464139"]


def get_all_offers():
    current = 0
    batch = 900
    total = get_offers(limit=1)["totalCount"]
    print(total)
    offers = []
    while current < total:
        batch_offers = get_offers(limit=batch, offset=current)

        offers += batch_offers["offers"]
        current += batch_offers["count"]

    with open("all_offers.json", "w") as file:
        file.write(json.dumps(offers, indent=4))

    return offers


def update_offers_status_sync(offers, action):
    batch_size = 1000
    max_offers_per_minute = 9000
    start_index = 0

    # headers_ = {
    #     'Authorization': f'Bearer {access_token}',
    #     'Accept': 'application/vnd.allegro.public.v1+json',
    #     'Content-Type': 'application/vnd.allegro.public.v1+json'
    # }

    while start_index < len(offers):
        end_index = min(start_index + batch_size, len(offers))
        batch_offers = offers[start_index:end_index]

        payload = {
            "offerCriteria": [
                {
                    "offers": [{"id": offer.get('id')} for offer in batch_offers],
                    "type": "CONTAINS_OFFERS",
                }
            ],
            "publication": {
                "action": action,
            },
        }

        command_id = str(uuid.uuid4())
        url = f"https://api.allegro.pl/sale/offer-publication-commands/{command_id}"

        try:
            response = requests.put(url, headers=headers, data=payload)
            if response.status_code == 201:
                print(f"Command {action}ed successfully. Command ID: {command_id}. {response.text}")
            else:
                print(f"Error {response.status_code}: {response.text}")
        except Exception as error:
            print(f"Error sending request: {error}")

        start_index += batch_size

        if start_index % max_offers_per_minute == 0:
            print("Waiting for 1 minute before processing more offers...")
            time.sleep(60)
        else:
            time.sleep(0.5)


def process_change_offer(id_):
    url = f"https://api.allegro.pl/sale/product-offers/{id_}"

    data = {
        "publication": {
            "status": "INACTIVE"
        }
    }

    result = requests.patch(url=url, headers=headers, data=json.dumps(data))
    if result.status_code in [200, 202]:
        print(f"success {id_} {result.text}")
    else:
        print()


def process_update_offers(offers):
    # to_draft = []
    
    for item in offers:
        if item["id"] in exclude_:
            continue
        else:
            if item["publication"]["status"] == "ENDED":
                process_change_offer(item["id"])

    # update_offers_status_sync(to_draft, "INACTIVE")


def process_delete_draft_offers(offers):

    for item in offers:
        if item["id"] in ...:
            continue
        else:
            if item["publication"]["status"] == "INACTIVE":
                delete_draft_offer(offer_id=item["id"])


def delete_draft_offer(offer_id):
    url = f"https://api.allegro.pl/sale/offers/{offer_id}"

    result = requests.delete(headers=headers, url=url)
    if result.status_code in [200, 204]:
        print(f"Success {offer_id}")
    else:
        print(f"error {offer_id}")


def get_offer(offer):

    url = f"https://api.allegro.pl/sale/product-offers/{offer}"

    response = requests.get(url, headers=headers)
    # response.raise_for_status()
    resp = json.loads(response.text)

    with open("single_offer_details.json", "w") as file:
        file.write(json.dumps(resp, indent=4))

    # print(len(response.json()["offers"]))
def category_by_id(cat_id):

    url = f"https://api.allegro.pl/sale/categories/{cat_id}"

    response = requests.get(url, headers=headers)
    resp = json.loads(response.text)

    with open("categories.json", "w") as file:
        file.write(json.dumps(resp, indent=4))


def get_categories(cat_id: str | None = None):
    if cat_id:
        params = {
            "parent.id": cat_id
        }
    else:
        params = {}

    url = f"https://api.allegro.pl/sale/categories"

    response = requests.get(url, headers=headers, params=params)
    resp = json.loads(response.text)

    return resp
    # with open("categories.json", "w") as file:
    #     file.write(json.dumps(resp, indent=4))


def get_categories_in_cat(cat_id: str):
    params = {
        "parent.id": cat_id
    }

    url = "https://api.allegro.pl/sale/categories"
    r = requests.get(url, headers=headers, params=params)
    data = r.json()

    categories = data.get("categories", [])

    # Будем собирать список категорий
    result = []
    for cat in categories:
        print(f"Category: {cat['name']}")
        # Проверяем, является ли категория листовой
        if cat["leaf"]:
            # Листовая категория - возвращаем её как объект
            result.append({
                "id": cat["id"],
                "name": cat["name"]
            })
        else:
            # Если не листовая, рекурсивно получаем её потомков
            children = get_categories_in_cat(cat["id"])
            result.append({
                "id": cat["id"],
                "name": cat["name"],
                "children": children
            })

    return result

def get_categories_tree():

    result = get_categories_in_cat("954b95b6-43cf-4104-8354-dea4d9b10ddf")

    with open("cat_tree.json", "w") as file:
        file.write(json.dumps(result, indent=2))


get_categories_tree()










def get_category_info(cat_id):

    url = f"https://api.allegro.pl/sale/categories/{cat_id}/parameters"

    response = requests.get(url, headers=headers)
    resp = json.loads(response.text)

    with open("categoriy_info.json", "w") as file:
        file.write(json.dumps(resp, indent=4))


def decode_token(token):
    decoded = jwt.decode(token, options={"verify_signature": False})
    print(decoded)
    print(type(decoded))


def get_data_for_rekman():
    url = "https://api.rekman.com.pl/cennik.php?email=aradzevich&password=GeVIOj&TylkoNaStanie=TRUE"
    response = requests.get(url)
    print(response.text)


def get_offers_with_missing_params():
    url = "https://api.allegro.pl/sale/offers/unfilled-parameters"
    params = {
        "limit": 1000
    }
    response = requests.get(url, params=params, headers=headers)

    with open("with_missing_params.json", "w") as file:
        file.write(json.dumps(response.json(), indent=4))

# get_offers_with_missing_params()


def get_params_supported_by_category(cat_id):
    url = f"https://api.allegro.pl/sale/categories/{cat_id}/parameters"

    response = requests.get(url, headers=headers)
    with open("params_supp_by_cat.json", "w") as file:
        file.write(json.dumps(response.json(), indent=4))


def get_products_search(ean: str):

    url = f"https://api.allegro.pl/sale/products"
    params = {
        "phrase": ean,
        "mode": "GTIN"
    }

    response = requests.get(url, headers=headers, params=params)
    with open("products_search.json", "w") as file:
        file.write(json.dumps(response.json(), indent=4))
    return response.json()


def get_product_details(product_id):

    url = f"https://api.allegro.pl/sale/products/{product_id}"

    response = requests.get(url, headers=headers)
    with open("product_details.json", "w") as file:
        file.write(json.dumps(response.json(), indent=4))


def get_responsible_persons():

    url = f"https://api.allegro.pl/sale/responsible-persons"

    response = requests.get(url, headers=headers)
    with open("responsible_persons.json", "w") as file:
        file.write(json.dumps(response.json(), indent=4))


def create_offer(prod_ean: str):

    url = f"https://api.allegro.pl/sale/product-offers"
    product = get_products_search(prod_ean)["products"][0]
    params = {
        "productSet": [
            {
                "product": {"id": product["id"]},
                "quantity": {
                    "value": 1
                },
            }
        ],
        "stock": {
            "available": 11,
            "unit": "UNIT"
        },
        "language": "pl-PL",
        "category": {"id": product["category"]["id"]},
        # "parameters": product["parameters"],
        "name": product["name"],
        "sellingMode": {
            "format": "BUY_NOW",
            "price": {
                "amount": "1335.70",
                "currency": "PLN"
            },
        },
        "external": {"id": "test_id_1234"}
    }
    # new_params = json.dumps(params)
    # print(params)
    response = requests.post(url, headers=headers, data=params)
    # response = requests.post(url, headers=headers, data=new_params)

    print(response.json())

    # with open("response.json", "w") as file:
    #     file.write(json.dumps(response.json(), indent=4))


def check():
    url = "https://api.allegro.pl/me"
    response = requests.get(url, headers=headers)
    print(response.json())

def search_all_offers():

    url = "https://api.allegro.pl/offers/listing"
    data = {
        "phrase": "Arvex 2053.0001 resin mixing tip"
    }
    response = requests.get(url, headers=headers, data=json.dumps(data))

    print(response.json())

def handle_file(path: str):
    with open(path, "r") as file:
        data = json.loads(file.read())
    ids = [item["allegro_oferta_id"] for item in data if item["allegro_we_sell_it"]]
    print(len(ids))
    with open(f"{path}.txt", "w") as file:
        file.write(json.dumps(ids))

    with open(f"{path}_for_updater.txt", "w") as file:
        file.write(",".join(ids))

# handle_file("/home/izbushko/Downloads/Allegro_files/unimet_cat_147677/SuppliersSkuMap.fursollerhouse_res.json")

# get_categories()

# get_product_details("5d621d3f-adbd-4441-be91-cf3698a44308")
# offers_ = get_all_offers()
# process_change_offer(13410553170)
# delete_draft_offer(13410553170)

# inactive = []
# for o in offers_:
#     if o["publication"]["status"] == "INACTIVE":
#         inactive.append(o)
# print(len(inactive))
# process_update_offers(offers_)

