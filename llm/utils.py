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
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Schemas ship alongside this package. Resolving them from the package directory
# keeps imports working regardless of the process working directory, which the
# previous relative "schemas/..." paths depended on.
_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def create_open_ai_client():
    """Build an OpenAI client, optionally against a self-hosted OPENAI_URL.

    TLS verification is always enabled. The previous implementation passed
    ``verify=False`` whenever ``OPENAI_URL`` was set, which allowed any network
    position between this service and the model endpoint to read the API key and
    to rewrite the generated transaction payload (chain, token, recipient,
    amount) before it was signed by the caller.

    Set ``OPENAI_CA_BUNDLE`` to the path of a PEM bundle when the endpoint uses
    a private certificate authority.
    """
    base_url = os.getenv("OPENAI_URL")
    if not base_url:
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    ca_bundle = os.getenv("OPENAI_CA_BUNDLE")
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=base_url,
        http_client=httpx.Client(
            # Redirects are not followed: a redirect from the configured host
            # would replay the Authorization header, and therefore the API key,
            # to whatever host the response pointed at.
            follow_redirects=False,
            verify=ca_bundle if ca_bundle else True,
        ),
    )


def load_schema(schema_name):
    """Load a JSON schema that is bundled with this package.

    Args:
        schema_name: File name or path fragment of the schema, e.g.
            ``"schemas/swap.json"`` or ``"swap.json"``.

    Raises:
        ValueError: if ``schema_name`` resolves outside the schema directory.
    """
    candidate = (_SCHEMA_DIR / Path(schema_name).name).resolve()
    if candidate.parent != _SCHEMA_DIR:
        raise ValueError(f"Refusing to load schema outside {_SCHEMA_DIR}: {schema_name}")
    with candidate.open("r", encoding="utf-8") as file:
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
    raise ValueError(f"transaction_type not supported: {transaction_type!r}")


class ModelOutputError(ValueError):
    """The model returned JSON that does not describe a transaction we can execute.

    Model output is untrusted input: the text the model is summarising comes from
    the end user, so a prompt-injection attempt can steer the JSON toward an
    unknown chain, an unlisted token, or a missing field. Raising a distinct
    error type lets callers reject the response instead of indexing into the
    contract tables with attacker-influenced keys.
    """


def resolve_token_address(contracts, chain, symbol, field_name):
    """Map a (chain, token symbol) pair from model output to a known contract address.

    Args:
        contracts: Nested mapping of chain -> token symbol -> contract address.
        chain: Chain name produced by the model.
        symbol: Token symbol produced by the model.
        field_name: Name of the field being resolved, used in error messages.

    Returns:
        The checksummed contract address string from the allowlist.

    Raises:
        ModelOutputError: if the chain or symbol is absent from the allowlist, or
            either value is not a string.
    """
    if not isinstance(chain, str) or not isinstance(symbol, str):
        raise ModelOutputError(
            f"{field_name}: chain and token symbol must both be strings, "
            f"got chain={type(chain).__name__}, symbol={type(symbol).__name__}"
        )

    chain_tokens = contracts.get(chain)
    if chain_tokens is None:
        raise ModelOutputError(
            f"Unsupported chain {chain!r}; supported chains: {sorted(contracts)}"
        )

    address = chain_tokens.get(symbol)
    if address is None:
        raise ModelOutputError(
            f"Unsupported token {symbol!r} on chain {chain!r}; "
            f"supported tokens: {sorted(chain_tokens)}"
        )
    return address


def require_fields(payload, fields):
    """Assert that model output is a dict containing every name in ``fields``.

    Raises:
        ModelOutputError: if ``payload`` is not a mapping or a field is missing.
    """
    if not isinstance(payload, dict):
        raise ModelOutputError(
            f"Expected a JSON object from the model, got {type(payload).__name__}"
        )
    missing = [field for field in fields if field not in payload]
    if missing:
        raise ModelOutputError(f"Model output is missing required field(s): {missing}")
    return payload

