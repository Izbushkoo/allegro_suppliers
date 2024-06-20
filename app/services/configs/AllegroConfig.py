supplier_settings = {
    "pgn": {
        "skuPrefix": "PGN_",
        "handlingTime": 3,
        "xmlPath": {
            "products": "offers.product",
            "sku": "pgncode",
            "price": "price",
            "vat": "vat",
            "stock": "availability",
            "ean": "ean",
            "category": "category"
        },
        "priceRanges": [
            {"maxPrice": 10, "factor": "add", "value": 12},
            {"maxPrice": 20, "factor": "multiply", "value": 3.5},
            {"maxPrice": 40, "factor": "multiply", "value": 3},
            {"maxPrice": 60, "factor": "multiply", "value": 2.75},
            {"maxPrice": 100, "factor": "multiply", "value": 2.5},
            {"maxPrice": 200, "factor": "multiply", "value": 2.25},
            {"maxPrice": 400, "factor": "multiply", "value": 2},
            {"maxPrice": 600, "factor": "multiply", "value": 1.9},
            {"maxPrice": 800, "factor": "multiply", "value": 1.8},
            {"maxPrice": 1000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 1500, "factor": "multiply", "value": 1.7},
            {"maxPrice": 3000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 5000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 9999, "factor": "multiply", "value": 1.7},
            {"maxPrice": 99999, "factor": "multiply", "value": 1.7},
        ],
        "isVatIncluded": True,
        "applyMultiplier": False,
        "customMultiplier": 0.7,
        "applyCustomMultipliers": False,
        "customMultipliers": {
            "productA": 1.2,
            "productB": 1.1,
            "productC": 0.9
        }
    },
    "unimet": {
        "skuPrefix": "UNIMET_",
        "handlingTime": 3,
        "xmlPath": {
            "products": "items.item",
            "sku": "INDEKS",
            "price": "CENA_KLIENTA_MIN",
            "vat": "VAT",
            "stock": "STAN_NA_MAGAZYNIE",
            "ean": "EAN",
            "category": "KATEGORIE"
        },
        "priceRanges": [
            {"maxPrice": 10, "factor": "add", "value": 12},
            {"maxPrice": 20, "factor": "multiply", "value": 3.5},
            {"maxPrice": 40, "factor": "multiply", "value": 3},
            {"maxPrice": 60, "factor": "multiply", "value": 2.75},
            {"maxPrice": 100, "factor": "multiply", "value": 2.5},
            {"maxPrice": 200, "factor": "multiply", "value": 2.25},
            {"maxPrice": 400, "factor": "multiply", "value": 2},
            {"maxPrice": 600, "factor": "multiply", "value": 1.9},
            {"maxPrice": 800, "factor": "multiply", "value": 1.8},
            {"maxPrice": 1000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 1500, "factor": "multiply", "value": 1.7},
            {"maxPrice": 3000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 5000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 9999, "factor": "multiply", "value": 1.7},
            {"maxPrice": 99999, "factor": "multiply", "value": 1.7},
        ],
        "isVatIncluded": False,
        "applyMultiplier": False,
        "customMultiplier": 0.7,
        "applyCustomMultipliers": False,
        "customMultipliers": {
            "productA": 1.2,
            "productB": 1.1,
            "productC": 0.9
        }
    },
    "hurtprem": {
        "skuPrefix": "HURTP_",
        "handlingTime": 3,
        "xmlPath": {
            "products": "offers.group.o",
            "sku": "@id",
            "price": "@price",
            "vat": "vat",
            "stock": "@stock",
            "ean": "attrs.ean",
            "category": "cat"
        },
        "priceRanges": [
            {"maxPrice": 10, "factor": "add", "value": 12},
            {"maxPrice": 20, "factor": "multiply", "value": 3.5},
            {"maxPrice": 40, "factor": "multiply", "value": 3},
            {"maxPrice": 60, "factor": "multiply", "value": 2.75},
            {"maxPrice": 100, "factor": "multiply", "value": 2.5},
            {"maxPrice": 200, "factor": "multiply", "value": 2.25},
            {"maxPrice": 400, "factor": "multiply", "value": 2},
            {"maxPrice": 600, "factor": "multiply", "value": 1.9},
            {"maxPrice": 800, "factor": "multiply", "value": 1.8},
            {"maxPrice": 1000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 1500, "factor": "multiply", "value": 1.7},
            {"maxPrice": 3000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 5000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 9999, "factor": "multiply", "value": 1.7},
            {"maxPrice": 99999, "factor": "multiply", "value": 1.7},
        ],
        "isVatIncluded": True,
        "applyMultiplier": False,
        "customMultiplier": 0.7,
        "applyCustomMultipliers": False,
        "customMultipliers": {
            "productA": 1.2,
            "productB": 1.1,
            "productC": 0.9
        }
    },
    "rekman": {
        "skuPrefix": "RKMN_",
        "handlingTime": 3,
        "xmlPath": {
            "products": "CENNIK.ARTYKUL",
            "sku": "KOD_REKMAN_NEW",
            "price": "CENA_NETTO_BEZ_RABATU",
            "vat": "PODATEK",
            "stock": "PRODUCTS_QUANTITY",
            "ean": "KOD_KRESKOWY",
            "category": "CATEGORY_NAME"
        },
        "priceRanges": [
            {"maxPrice": 10, "factor": "add", "value": 12},
            {"maxPrice": 20, "factor": "multiply", "value": 3.5},
            {"maxPrice": 40, "factor": "multiply", "value": 3},
            {"maxPrice": 60, "factor": "multiply", "value": 2.75},
            {"maxPrice": 100, "factor": "multiply", "value": 2.5},
            {"maxPrice": 200, "factor": "multiply", "value": 2.25},
            {"maxPrice": 400, "factor": "multiply", "value": 2},
            {"maxPrice": 600, "factor": "multiply", "value": 1.9},
            {"maxPrice": 800, "factor": "multiply", "value": 1.8},
            {"maxPrice": 1000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 1500, "factor": "multiply", "value": 1.7},
            {"maxPrice": 3000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 5000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 9999, "factor": "multiply", "value": 1.7},
            {"maxPrice": 99999, "factor": "multiply", "value": 1.7},
        ],
        "isVatIncluded": False,
        "applyMultiplier": False,
        "customMultiplier": 0.7,
        "applyCustomMultipliers": False,
        "customMultipliers": {
            "productA": 1.2,
            "productB": 1.1,
            "productC": 0.9
        }
    },
    "growbox": {
        "skuPrefix": "GRBX_",
        "handlingTime": 3,
        "xmlPath": {
            "products": "products.product",
            "sku": "sku",
            "price": "priceAfterDiscountNet",
            "vat": "vat",
            "stock": "qty",
            "ean": "",
            "category": ""
        },
        "priceRanges": [
            {"maxPrice": 10, "factor": "add", "value": 22},
            {"maxPrice": 20, "factor": "multiply", "value": 3.5},
            {"maxPrice": 40, "factor": "multiply", "value": 3},
            {"maxPrice": 60, "factor": "multiply", "value": 2.75},
            {"maxPrice": 100, "factor": "multiply", "value": 2.5},
            {"maxPrice": 200, "factor": "multiply", "value": 2.25},
            {"maxPrice": 400, "factor": "multiply", "value": 2},
            {"maxPrice": 600, "factor": "multiply", "value": 1.9},
            {"maxPrice": 800, "factor": "multiply", "value": 1.8},
            {"maxPrice": 1000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 1500, "factor": "multiply", "value": 1.7},
            {"maxPrice": 3000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 5000, "factor": "multiply", "value": 1.7},
            {"maxPrice": 9999, "factor": "multiply", "value": 1.7},
            {"maxPrice": 99999, "factor": "multiply", "value": 1.7},
        ],
        "isVatIncluded": False,
        "applyMultiplier": False,
        "customMultiplier": 0.7,
        "applyCustomMultipliers": False,
        "customMultipliers": {
            '01285': 0.8,
            '01287': 0.8,
            '01584': 0.8,
            '01585': 0.8,
            '01586': 0.8,
            '01587': 0.8,
            '01588': 0.8,
            '01589': 0.8,
            '01590': 0.8,
            '01591': 0.8,
            '01592': 0.8,
            '01593': 0.8,
            '01594': 0.8,
            '01595': 0.8,
            '01596': 0.8,
            '01597': 0.8,
            '01598': 0.8,
            '01599': 0.8,
            '01600': 0.8,
            '01601': 0.8,
            '01602': 0.8,
            '01603': 0.8,
            '01604': 0.8,
            '01606': 0.8,
            '01607': 0.8,
            '01610': 0.8,
            '01611': 0.8,
            '01613': 0.8,
            '01614': 0.8,
            '01615': 0.8,
            '01616': 0.8,
            '01617': 0.8,
            '01618': 0.8,
            '01619': 0.8,
            '01620': 0.8,
            '01621': 0.8,
            '01622': 0.8,
            '01623': 0.8,
            '01624': 0.8,
            '01625': 0.8,
            '01626': 0.8,
            '01627': 0.8,
            '01629': 0.8,
            '01630': 0.8,
            '01631': 0.8,
            '01632': 0.8,
            '01633': 0.8,
            '01634': 0.8,
            '01635': 0.8,
            '01636': 0.8,
            '01637': 0.8,
            '01638': 0.8,
            '01639': 0.8,
            '01640': 0.8,
            '01641': 0.8,
            '01642': 0.8,
            '01644': 0.8,
            '01645': 0.8,
            '01646': 0.8,
            '01647': 0.8,
            '01648': 0.8,
            '01649': 0.8,
            '01650': 0.8,
            '01651': 0.8,
            '01652': 0.8,
            '01653': 0.8,
            '01654': 0.8,
            '01655': 0.8,
            '01696': 0.8,
            '01697': 0.8,
            '01806': 0.8,
            '01876': 0.8,
            '01948': 0.8,
            '01949': 0.8,
            '01990': 0.8,
            '01991': 0.8,
            '01992': 0.8,
            '02046': 0.8,
            '02230': 0.8,
            '02231': 0.8,
            '02232': 0.8,
            '02238': 0.8,
            '02344': 0.8,
            '02345': 0.8,
            '02419': 0.8,
            '02439': 0.8,
            '02472': 0.8,
            '02487': 0.8,
            '02488': 0.8,
            '02496': 0.8,
            '02497': 0.8,
            '02498': 0.8,
            '02570': 0.8,
            '02571': 0.8,
            '02572': 0.8,
            '02666': 0.8,
            '02667': 0.8,
            '02712': 0.8,
            '02743': 0.8,
            '02783': 0.8,
            '02784': 0.8,
            '02785': 0.8,
            '02955': 0.8,
            '02956': 0.8,
            '02957': 0.8,
            '02958': 0.8,
            '02971': 0.8,
            '03021': 0.8,
            '03022': 0.8,
            '03023': 0.8,
            '03024': 0.8,
            '03026': 0.8,
            '03056': 0.8,
            '03057': 0.8,
            '03058': 0.8,
            '03065': 0.8,
            '03113': 0.8,
            '03114': 0.8,
            '03115': 0.8,
            '03116': 0.8,
            '03117': 0.8,
            '03213': 0.8,
            '03236': 0.8,
            '03249': 0.8,
            '03360': 0.8,
            '03365': 0.8,
            '03366': 0.8,
            '03414': 0.8,
            '03473': 0.8,
            '03547': 0.8,
            '03628': 0.8,
            '03629': 0.8,
            '03634': 0.8,
            '03642': 0.8,
            '03644': 0.8,
            '03799': 0.8,
            '03854': 0.8,
            '03887': 0.8,
            '03894': 0.8,
            '03895': 0.8,
            '04042': 0.8,
            '04043': 0.8,
            '04044': 0.8,
            '04045': 0.8,
            '04046': 0.8,
            '04047': 0.8,
            '04048': 0.8,
            '04049': 0.8,
            '04050': 0.8,
            '04053': 0.8,
            '04054': 0.8,
            '04191': 0.8,
            '04198': 0.8,
            '04199': 0.8,
            '04262': 0.8,
            '04263': 0.8,
            '04264': 0.8,
            '04272': 0.8,
            '04273': 0.8,
            '04274': 0.8,
            '04291': 0.8,
            '04319': 0.8,
            '04407': 0.8,
            '04494': 0.8,
            '04495': 0.8,
            '04601': 0.8,
            '04602': 0.8,
            '04717': 0.8,
            '04718': 0.8,
            '04795': 0.8,
            '04807': 0.8,
            '04872': 0.8,
            '04925': 0.8,
            '04928': 0.8,
            '04929': 0.8,
            '04930': 0.8,
            '04931': 0.8,
            '04932': 0.8,
            '04933': 0.8,
            '04934': 0.8,
            '04935': 0.8,
            '04936': 0.8,
            '04950': 0.8,
            '05156': 0.8,
            '05281': 0.8,
            '05529': 0.8,
            '05533': 0.8,
            '05644': 0.8,
            '05645': 0.8,
            '05646': 0.8
        }
    }
}
