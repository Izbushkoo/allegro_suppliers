AmazonSettings = {
    'tsvHeaders': {
        'remove_items': [
            'seller-sku',
            'add-delete'
        ],
        'add_items': [
            'sku',
            'product-id',
            'product-id-type',
            'price',
            'item-condition',
            'quantity',
            'add-delete',
            'handling-time',
            'merchant_shipping_group_name',
            'expedited-shipping',
        ]
    },
    'fileType': {
        'remove_items': '_remove',
        'add_items': '_add',
    },
    'priceMultiplier': {
        'DE': 1.1
    }
}
