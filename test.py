import json

import jwt
import requests


access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX25hbWUiOiIxMDI3NTgyODAiLCJzY29wZSI6WyJhbGxlZ3JvOmFwaTpvcmRlcnM6cmVhZCIsImFsbGVncm86YXBpOmZ1bGZpbGxtZW50OnJlYWQiLCJhbGxlZ3JvOmFwaTpwcm9maWxlOndyaXRlIiwiYWxsZWdybzphcGk6ZnVsZmlsbG1lbnQ6d3JpdGUiLCJhbGxlZ3JvOmFwaTpzYWxlOm9mZmVyczp3cml0ZSIsImFsbGVncm86YXBpOmJpbGxpbmc6cmVhZCIsImFsbGVncm86YXBpOmNhbXBhaWducyIsImFsbGVncm86YXBpOmRpc3B1dGVzIiwiYWxsZWdybzphcGk6YmlkcyIsImFsbGVncm86YXBpOnNhbGU6b2ZmZXJzOnJlYWQiLCJhbGxlZ3JvOmFwaTpzaGlwbWVudHM6d3JpdGUiLCJhbGxlZ3JvOmFwaTpvcmRlcnM6d3JpdGUiLCJhbGxlZ3JvOmFwaTphZHMiLCJhbGxlZ3JvOmFwaTpwYXltZW50czp3cml0ZSIsImFsbGVncm86YXBpOnNhbGU6c2V0dGluZ3M6d3JpdGUiLCJhbGxlZ3JvOmFwaTpwcm9maWxlOnJlYWQiLCJhbGxlZ3JvOmFwaTpyYXRpbmdzIiwiYWxsZWdybzphcGk6c2FsZTpzZXR0aW5nczpyZWFkIiwiYWxsZWdybzphcGk6cGF5bWVudHM6cmVhZCIsImFsbGVncm86YXBpOnNoaXBtZW50czpyZWFkIiwiYWxsZWdybzphcGk6bWVzc2FnaW5nIl0sImFsbGVncm9fYXBpIjp0cnVlLCJpc3MiOiJodHRwczovL2FsbGVncm8ucGwiLCJleHAiOjE3MjE2NzIwOTYsImp0aSI6ImFjMTFhZjhkLTdjZjgtNDczMi1hZjAxLWI3ZTM2MDVmNzhmOSIsImNsaWVudF9pZCI6IjdiNDFkOTE4ZDVlMDQ4NDE4NGRlMzE1ODIwMjkzODcxIn0.sblMGt1SCfS2smG4Hnj2ZjYZdNxNd6d2H8TqX2FbeZKz_XcduhC4SOfO37CkqEYVMt7hxY4ZKmyQ53FZAmeqNV85Vv_QKsL9-MijRIVeSW0hCjnDsayUogDUGDvtg8mvNju8QAh8e1tzQHfF0gWPFu8N5448Fh26nsXKaOtaE9K6fSdgYE2UcO95Cw9QREMr9fd1U67NzNcZTl4Juhc9BQHJbW7QZMRriUzoxkWSONOKdLwEE6p1WrK3OVZ0GnanaUckrS0biIFlym7cID1m3DekV8_UxAbUeQF5hUWEU3JCemDLb_X59i8aqyIKBNSuFNcRL1JcoLLq2UuhdJ_HaQ"


headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/vnd.allegro.public.v1+json",
    "Accept": "application/vnd.allegro.public.v1+json",
}

def get_offers():
    params = {
        "name": "wkręt do drewna",
        # "name": "",
        "limit": 500
    }

    url = f"https://api.allegro.pl/sale/offers"

    response = requests.get(url, headers=headers, params=params)
    # response.raise_for_status()
    resp = json.loads(response.text)

    with open("products.json", "w") as file:
        file.write(json.dumps(resp, indent=4))

    print(len(response.json()["offers"]))


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


def get_product_details(product_id):

    url = f"https://api.allegro.pl/sale/products/{product_id}"

    response = requests.get(url, headers=headers)
    with open("product_details.json", "w") as file:
        file.write(json.dumps(response.json(), indent=4))

# get_offer(13409953686)
# get_params_supported_by_category(cat_id=126200)
# get_offers_with_missing_params()
get_product_details("dd2bca59-ee64-42c4-85b1-be29256b61d7")