import json
import os.path

import jwt
import requests


access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX25hbWUiOiIxMjI2NTc4MDAiLCJzY29wZSI6WyJhbGxlZ3JvOmFwaTpvcmRlcnM6cmVhZCIsImFsbGVncm86YXBpOmZ1bGZpbGxtZW50OnJlYWQiLCJhbGxlZ3JvOmFwaTpwcm9maWxlOndyaXRlIiwiYWxsZWdybzphcGk6c2FsZTpvZmZlcnM6d3JpdGUiLCJhbGxlZ3JvOmFwaTpmdWxmaWxsbWVudDp3cml0ZSIsImFsbGVncm86YXBpOmJpbGxpbmc6cmVhZCIsImFsbGVncm86YXBpOmNhbXBhaWducyIsImFsbGVncm86YXBpOmRpc3B1dGVzIiwiYWxsZWdybzphcGk6c2FsZTpvZmZlcnM6cmVhZCIsImFsbGVncm86YXBpOnNoaXBtZW50czp3cml0ZSIsImFsbGVncm86YXBpOmJpZHMiLCJhbGxlZ3JvOmFwaTpvcmRlcnM6d3JpdGUiLCJhbGxlZ3JvOmFwaTphZHMiLCJhbGxlZ3JvOmFwaTpwYXltZW50czp3cml0ZSIsImFsbGVncm86YXBpOnNhbGU6c2V0dGluZ3M6d3JpdGUiLCJhbGxlZ3JvOmFwaTpwcm9maWxlOnJlYWQiLCJhbGxlZ3JvOmFwaTpyYXRpbmdzIiwiYWxsZWdybzphcGk6c2FsZTpzZXR0aW5nczpyZWFkIiwiYWxsZWdybzphcGk6cGF5bWVudHM6cmVhZCIsImFsbGVncm86YXBpOnNoaXBtZW50czpyZWFkIiwiYWxsZWdybzphcGk6bWVzc2FnaW5nIl0sImFsbGVncm9fYXBpIjp0cnVlLCJpc3MiOiJodHRwczovL2FsbGVncm8ucGwiLCJleHAiOjE3MjQ4ODU0MjEsImp0aSI6IjMyZTRjZmZlLThkMGItNDk0OS1hN2JkLWQ4MmY3OWM4MTkwYSIsImNsaWVudF9pZCI6ImJkZDRkYTA1MThkOTQ5YzRiMDkxYTZhYmU0ZmQ4M2Y3In0.dVkox6QwX4K_aaHyFPhBuLcTNk2mq9KU47DiU17UcGDGiUlRbVZQ6VJUg2SiLR-d6NXIu_ICrzMBVNeUsgoz1EORuw-wxD9DawjiBTFd3AZ6ebVUPElqIfl1YGrskVOp_9hJtAsztOjHnCqLU9KR5AhndY6EpXUHLnG1RMJYlRdVddY0Fs6G_G83GzhS2tzbLcj6ogkQQVt2Do250rzRqKU4W_nARlVLKfdkKuUN4PyqvnsWtmwbCHcaKqGL1yfmS6NkMl-bxrE3921ixmMHISnidjjibjAu9Qw7k7-T8Pv4CzXdW9oLDaC4lR3WaHAea5WMB4zEZFMMQdWWbc4Hag"


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

    all_skus = []
    for item in offers:
        if item["external"]:
            all_skus.append(item["external"]["id"])

    with open("all_skus.json", "w") as file:
        file.write(json.dumps(all_skus, indent=4))

    return all_skus


def get_offer(offer):

    params = {
        "name": "wkręt do drewna",
        # "name": "",
        "limit": 500
    }

    url = f"https://api.allegro.pl/sale/product-offers/{offer}"

    response = requests.get(url, headers=headers)
    # response.raise_for_status()
    resp = json.loads(response.text)

    with open("single_offer_details.json", "w") as file:
        file.write(json.dumps(resp, indent=4))

    # print(len(response.json()["offers"]))


def get_categories():

    params = {
        "parent.id": 5317
    }

    url = f"https://api.allegro.pl/sale/categories"

    response = requests.get(url, headers=headers, params=params)
    resp = json.loads(response.text)

    # new = list(filter(lambda x: x['leaf'], resp["categories"]))

    with open("categories.json", "w") as file:
        file.write(json.dumps(resp, indent=4))


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


search_all_offers()


# check()


# get_offer(13409953686)
# get_params_supported_by_category(cat_id=67456)
# get_products_search("4260223021305")
# create_offer("4260223021305")
# check()
# get_responsible_persons()
# get_offers_with_missing_params()
# get_product_details("8db3241b-8552-4eab-880a-44bb7a317123")
# get_all_offers_filter("HURTP")
# get_all_offers()

# def filter_local_file(supplier, word):
#
#     path = os.path.join("/home/izbushko/some_found_descriptions", f"{supplier}.json",)
#     with open(path, "r") as file:
#         data = json.loads(file.read())
#     filtered_dict = {}
#     count = 0
#     for key, value in data.items():
#         for item in value:
#             if
#         pattern = re.compile(re.escape(word), re.IGNORECASE)
#         if pattern.search():
#
