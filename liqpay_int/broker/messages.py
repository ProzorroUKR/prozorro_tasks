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
"Unique purchase ID in your shop. Maximum length is 255 symbols. " \
"Optional. If not passed will be automatically filled."

DESC_TICKET_POST = "" \
"# Send a receipt to the specified client's email.\n" \
"API to work with https://www.liqpay.ua/documentation/api/information/ticket/\n" \
"## How it works.\n" \
"1. Form a request according to documentation.\n" \
"2. Client will receive a letter with receipt to the specified email.\n" \
"3. You will receive status of request execution.\n"

DESC_TICKET_EMAIL = "Email for a reciept sending"
DESC_TICKET_ORDER_ID = "order_id of successful payment"
DESC_TICKET_LANG = "Customer's language ru, uk, en"
DESC_TICKET_STAMP = "Sign of receipt with stamp. " \
"Possible values: " \
"true - send receipt with print, " \
"false - send receipt without printing."

DESC_SIGNATURE_POST = "" \
"Get a signature\n" \
"The company sends a request for payment, with transfer of the server_url.\n" \
"After processing the operation by processing LiqPay and obtaining the final status, \n" \
"a POST request will be sent to your server with data and signature, where:\n" \
"- `data` - json string with APIs parameters encoded by the function `base64, base64_encode( json_string )`\n" \
"- `signature` - is the unique signature of each request `base64_encode( sha1( private_key + data + private_key)` )\n" \
"- `base64_encode` - returns a string encoded by the base64\n" \
"- `sha1` - returns the hash as a binary string of 20 characters.\n\n" \
"To authenticate a request from a LiqPay server, you must:\n\n" \
"- send the data received in response from LiqPay and get signature in response\n" \
"- the final signature must be compared with the received from Callback from LiqPay,\n" \
"- if the signature is identical, then you have received a genuine response from the server of LiqPay \n" \
"(not changed by a third party / without the intervention of third parties) and you can fulfill obligations to the \n" \
"customer on payment, in accordance with the received payment status."

SERVER_ID_DESC = "An optional server id that will be used as cookie to request external api"
