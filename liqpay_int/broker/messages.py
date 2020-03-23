DESC_REQUEST_SANDBOX = "" \
"Enable test mode. " \
"Details: https://www.liqpay.ua/documentation/api/sandbox."

DESC_CHECKOUT_POST = "" \
"# Get a payment link.\n" \
"API to work with https://www.liqpay.ua/documentation/api/aquiring/privatpay/\n" \
"## How it works.\n" \
"1. To get a link, form a request according to the technical documentation.\n" \
"2. Attach a link to the pay button.\n" \
"3. When clicking on the button, redirect the client to the link.\n"

DESC_CHECKOUT_AMOUNT = "Payment amount"
DESC_CHECKOUT_CURR = "Payment currency"
DESC_CHECKOUT_DESC = "Payment description"
DESC_CHECKOUT_LANG = "Customer's language ru, uk, en"
DESC_CHECKOUT_RESULT_URL = "" \
"URL of your shop where the buyer would be redirected " \
"after completion of the purchase." \
"Maximum length 510 symbols"
DESC_CHECKOUT_SERVER_URL = "" \
"URL API in your store for notifications " \
"of payment status change. " \
"Maximum length is 510 symbols. " \
"Details: https://www.liqpay.ua/documentation/api/callback."
DESC_CHECKOUT_ORDER_ID = "" \
"Unique purchase ID in your shop. " \
"Maximum length is 255 symbols"

DESC_TICKET_POST = "" \
"# Send a receipt to the specified client's email.\n" \
"API to work with https://www.liqpay.ua/documentation/api/information/ticket/\n" \
"## How it works.\n" \
"1. Form a request according to documentation.\n" \
"2. Client will receive a letter with receipt to the specified email.\n" \
"3. You will receive status of request execution.\n"

DESC_TICKET_EMAIL = "Email for reciept sending"
DESC_TICKET_ORDER_ID = "order_id of successful payment"
DESC_TICKET_LANG = "Customer's language ru, uk, en"
DESC_TICKET_STAMP = "Sign of receipt with stamp. " \
"Possible values: " \
"true - send receipt with print, " \
"false - send receipt without printing."
