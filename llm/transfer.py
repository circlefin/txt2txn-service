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
from .utils import (
    ModelOutputError,
    create_open_ai_client,
    get_token_contracts,
    load_schema,
    require_fields,
    resolve_token_address,
)

# Load the transfer schema
transfer_schema = load_schema("schemas/transfer.json")

# Initialize OpenAI client
client = create_open_ai_client()

token_contracts = get_token_contracts("transfer")


def convert_transfer_intent(user_input):
    """ Convert a user-provided sentence describing a token transfer into a JSON object based on the transfer schema. """

    # System message to set up the context for the AI
    system_message = {
        "role": "system",
        "content": "Please analyze the following transaction text and fill out the JSON schema based on the provided details. All prices are assumed to be in USD."
    }

    # Schema context message
    transfer_schema_message = {
        "role": "system",
        "content": "Simple Transfer Schema:\n" + json.dumps(transfer_schema, indent=2)
    }

    # User message with the transaction text
    user_message = {
        "role": "user",
        "content": user_input
    }

    # Additional instructions
    instructions_schema_message = {
        "role": "system",
        "content": "The outputted JSON should be an instance of the schema. Never output the schema itself, but instead fill out its values. It is not necessary to include the parameters/contraints that are not directly related to the data provided. If no chain is specified to excecute the transaction on, default to 'mainnet'",
    }
    # A failed completion must abort the request. The previous version caught the
    # exception, printed it, and then read `completion.choices` regardless, which
    # raised UnboundLocalError and masked the real upstream failure.
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            system_message,
            transfer_schema_message,
            instructions_schema_message,
            user_message,
        ],
        response_format={"type": "json_object"}
    )

    # Extract and interpret the last message from the completion
    filled_schema_text = completion.choices[0].message.content.strip()
    try:
        filled_schema = json.loads(filled_schema_text)
    except json.JSONDecodeError as error:
        raise ModelOutputError(
            "Model response was not valid JSON and cannot be turned into a transfer."
        ) from error

    # Model output is untrusted: validate the required fields and resolve the
    # token through the allowlist rather than indexing the contract table with
    # attacker-influenceable keys.
    require_fields(filled_schema, ("chain", "token"))
    filled_schema["token"] = resolve_token_address(
        token_contracts, filled_schema["chain"], filled_schema["token"], "token"
    )
    return filled_schema
