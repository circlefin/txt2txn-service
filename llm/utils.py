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

from openai import OpenAI
import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

def create_open_ai_client():
    if os.getenv("OPENAI_URL"):
        return OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_URL"),
            http_client=httpx.Client(
            follow_redirects=True,
            verify=False,
            ),
        )
    else:
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_schema(schema_path):
    """ Load a JSON schema from a file. """
    with open(schema_path, "r") as file:
        return json.load(file)

standard_token_contracts = {
    "base": {
        "$WETH": "0x4200000000000000000000000000000000000006",
        "$USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "$DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",

    },
    "mainnet": {
        "$WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "$USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "$DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "$EURC": "0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c"
    },
}

transfer_token_contracts = standard_token_contracts | {
    "sepolia": {
        "$WETH": "0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9",
        "$USDC": "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",
        "$DAI": "0xff34b3d4aee8ddcd6f9afffb6fe49bd371b8a357",
        "$EURC": "0x08210F9170F89Ab7658F0B5E3fF39b0E03C594D4"
    }
}

# Swap testnet tokens are cowswap-specific
swap_token_contracts = standard_token_contracts | {
    "sepolia": {
        "$USDC": "0xbe72E441BF55620febc26715db68d3494213D8Cb", # cowswap test USDC
        "$DAI": "0xB4F1737Af37711e9A5890D9510c9bB60e170CB0D" # cowswap test DAI
    }
}

def get_token_contracts(transaction_type):
    if transaction_type == "transfer":
        return transfer_token_contracts
    if transaction_type == "swap":
        return swap_token_contracts
    raise Exception("transaction_type not supported")

