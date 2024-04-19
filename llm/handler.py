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
from .utils import create_open_ai_client, load_schema

# Load the JSON schemas for swap and simple transfer
swap_schema = load_schema("schemas/swap.json")
transfer_schema = load_schema("schemas/transfer.json")

# Initialize OpenAI client
client = create_open_ai_client()

def classify_transaction(transaction_text):
    # System message explaining the task
    system_message = {
        "role": "system",
        "content": "Determine if the following transaction text is for a token swap or a transfer. Use the appropriate schema to understand the transaction. Return '1' for transfer, '2' for swap, and '0' for neither. Do not output anything besides this number. If one number is classified for the output, make sure to omit the other two in your generated response."
    }

    # Messages to set up schema contexts
    swap_schema_message = {
        "role": "system",
        "content": "[Swap Schema] Token Swap Schema:\n" + json.dumps(swap_schema, indent=2)
    }
    transfer_schema_message = {
        "role": "system",
        "content": "[Transfer Schema] Simple Transfer/Send Schema:\n" + json.dumps(transfer_schema, indent=2)
    }

    # User message with the transaction text
    user_message = {"role": "user", "content": transaction_text}

    # Sending the prompt to ChatGPT
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            system_message,
            swap_schema_message,
            transfer_schema_message,
            user_message,
        ]
    )

    # Extracting and interpreting the last message from the completion
    response = completion.choices[0].message.content.strip()
    print("classification: ", response)
    return get_valid_response(response)

def get_valid_response(response):
    valid_responses = ["0", "1", "2"]
    found = None
    
    for valid in valid_responses:
        # Count the occurrences of each valid response in the string
        if response.count(valid) == 1:
            if found is not None:
                # If another valid response was already found, return 0
                return 0
            found = int(valid)  # Store the found valid response
    
    return found if found is not None else 0