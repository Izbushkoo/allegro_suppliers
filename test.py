import json

import jwt
import requests


access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX25hbWUiOiIxMDI3NTgyODAiLCJzY29wZSI6WyJhbGxlZ3JvOmFwaTpvcmRlcnM6cmVhZCIsImFsbGVncm86YXBpOmZ1bGZpbGxtZW50OnJlYWQiLCJhbGxlZ3JvOmFwaTpwcm9maWxlOndyaXRlIiwiYWxsZWdybzphcGk6ZnVsZmlsbG1lbnQ6d3JpdGUiLCJhbGxlZ3JvOmFwaTpzYWxlOm9mZmVyczp3cml0ZSIsImFsbGVncm86YXBpOmJpbGxpbmc6cmVhZCIsImFsbGVncm86YXBpOmNhbXBhaWducyIsImFsbGVncm86YXBpOmRpc3B1dGVzIiwiYWxsZWdybzphcGk6YmlkcyIsImFsbGVncm86YXBpOnNhbGU6b2ZmZXJzOnJlYWQiLCJhbGxlZ3JvOmFwaTpzaGlwbWVudHM6d3JpdGUiLCJhbGxlZ3JvOmFwaTpvcmRlcnM6d3JpdGUiLCJhbGxlZ3JvOmFwaTphZHMiLCJhbGxlZ3JvOmFwaTpwYXltZW50czp3cml0ZSIsImFsbGVncm86YXBpOnNhbGU6c2V0dGluZ3M6d3JpdGUiLCJhbGxlZ3JvOmFwaTpwcm9maWxlOnJlYWQiLCJhbGxlZ3JvOmFwaTpyYXRpbmdzIiwiYWxsZWdybzphcGk6c2FsZTpzZXR0aW5nczpyZWFkIiwiYWxsZWdybzphcGk6cGF5bWVudHM6cmVhZCIsImFsbGVncm86YXBpOnNoaXBtZW50czpyZWFkIiwiYWxsZWdybzphcGk6bWVzc2FnaW5nIl0sImFsbGVncm9fYXBpIjp0cnVlLCJpc3MiOiJodHRwczovL2FsbGVncm8ucGwiLCJleHAiOjE3MjA0NjU2OTEsImp0aSI6IjE1ZWQyNTA1LTQ3NjctNGFkNC04Yzk5LTJkMzAzMmZjOWFjMiIsImNsaWVudF9pZCI6IjdiNDFkOTE4ZDVlMDQ4NDE4NGRlMzE1ODIwMjkzODcxIn0.ppsXgf7REzJWcx5t--XvONNEZmG-5XSFT9JNi09NlabzhmdXnTbXXHDHG_S70_DGIJUOUhhmV8jXdHfJWaN1Ize9colqlV1a00i_l2cK8Ac537apa8Cub1VJxPZq5YKw5VW1G8T71OtKDInGXN-ttd1zt2m5ayc4A6RPvfOJC_HSxoG3M2q7Dh5vxf1XZVuuWpIHitzhN9fm6fdrzDvXz_Hyiv4mDGbNVvrUkeQsAKISugWhEo-prLa_B1xhUcDyu4tpqguxe5h2qh4FhjHWA9qroqWbew5-KhV_MWhFj4BeGAXM7GK6wQpFJJiDCwZFr2RqCJrSUZAyQ9Kq_BGmAg"


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
