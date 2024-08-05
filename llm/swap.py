# Copyright (c) 2024 Blockchain at Berkeley.  All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# SPDX-License-Identifier: MIT

import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .utils import create_open_ai_client, load_schema, get_token_contracts

# load schema
swap_schema = load_schema("schemas/swap.json")

token_contracts = get_token_contracts("swap")

# Function to convert transaction text to JSON using appropriate schema
def convert_transaction(user_input):

    client = create_open_ai_client()

    # System message explaining the task and giving hints for each schema
    system_message = {
        "role": "system",
        "content": "Please analyze the following transaction text and fill out the JSON schema based on the provided details. All prices are assumed to be in USD."
    }

    # Messages to set up Schema
    swap_schema_message = {
        "role": "system",
        "content": "Token Swap Schema:\n" + json.dumps(swap_schema, indent=2),
    }

    instructions_schema_message = {
        "role": "system",
        "content": "The outputted JSON should be an instance of the schema. It is not necessary to include the parameters/contraints that are not directly related to the data provided.",
    }

    # User message with the transaction text
    user_message = {"role": "user", "content": user_input}

    # Sending the prompt to ChatGPT
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        response_format={"type": "json_object"},
        messages=[
            system_message,
            swap_schema_message,
            instructions_schema_message,
            user_message,
        ],
    )

    # Extracting the last message from the completion
    filled_schema_text = completion.choices[0].message.content.strip()
    try:
        filled_schema = json.loads(filled_schema_text)
    except json.JSONDecodeError:
        print("Error in decoding JSON. Response may not be in correct format.")
        filled_schema = {}

    print(filled_schema)
    filled_schema["fromAsset"] = token_contracts[filled_schema["chain"]][filled_schema["fromAsset"]]
    filled_schema["toAsset"] = token_contracts[filled_schema["chain"]][filled_schema["toAsset"]]

    return filled_schema
