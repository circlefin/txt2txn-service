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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field
import logging
import os
from llm import swap, handler, transfer
from llm.utils import ModelOutputError

logger = logging.getLogger(__name__)

# Allowed browser origins are configuration, not a source-code constant, so a
# deployment does not have to be patched to run outside localhost. Credentials
# are still only shared with an explicit origin allowlist (never "*").
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# Generic message returned to clients. Exception text from the model client can
# contain the upstream URL, request identifiers, and fragments of the prompt, so
# it is logged server-side and never echoed in the HTTP response.
UPSTREAM_ERROR = "Unable to process the request at this time."


class UserQuery(BaseModel):
    # A hard length bound keeps a single request from turning into an unbounded
    # (and billable) model call.
    question: str = Field(min_length=1, max_length=2000)


def _model_failure(endpoint: str, error: Exception) -> HTTPException:
    """Log an upstream/model failure and build a response that leaks nothing.

    ``ModelOutputError`` means the model produced something we refuse to turn
    into a transaction; that is a bad gateway response, not a server bug, and the
    message is safe to return because it only names allowlisted chains/tokens.
    """
    if isinstance(error, ModelOutputError):
        logger.warning("%s: rejected model output: %s", endpoint, error)
        return HTTPException(status_code=502, detail=str(error))
    logger.exception("%s: unexpected failure", endpoint)
    return HTTPException(status_code=500, detail=UPSTREAM_ERROR)


@app.post("/answer/")
async def get_answer(query: UserQuery):
    try:
        classification = handler.classify_transaction(query.question)
    except Exception as error:
        raise _model_failure("/answer/", error) from error

    # Unable to classify
    if classification == 1:
        query_type = "transfer"
        convert = transfer.convert_transfer_intent
    elif classification == 2:
        query_type = "swap"
        convert = swap.convert_transaction
    else:
        # Any other value (including 0) means the intent was not recognised. This
        # is a client-side problem, so it is a 422 rather than a 500, and the
        # branch is explicit: previously an unexpected classification left
        # `query_type` and `response` unbound and raised NameError.
        raise HTTPException(
            status_code=422,
            detail="Our backend was unable to classify your intent",
        )

    try:
        response = convert(query.question)
    except Exception as error:
        raise _model_failure("/answer/", error) from error

    return {"transaction_type": query_type, "response": response}


@app.post("/swap/")
async def get_swap(query: UserQuery):
    try:
        response = swap.convert_transaction(query.question)
    except Exception as error:
        raise _model_failure("/swap/", error) from error
    # The key was previously the `response` object itself rather than the string
    # "response", which made every successful call fail to serialise.
    return {"transaction_type": "swap", "response": response}


@app.post("/transfer/")
async def get_transfer(query: UserQuery):
    try:
        response = transfer.convert_transfer_intent(query.question)
    except Exception as error:
        raise _model_failure("/transfer/", error) from error
    return {"transaction_type": "transfer", "response": response}


@app.post("/classify/")
async def classify_query(query: UserQuery):
    try:
        response = handler.classify_transaction(query.question)
    except Exception as error:
        raise _model_failure("/classify/", error) from error
    return {"response": response}
