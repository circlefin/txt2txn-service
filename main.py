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

from pydantic import BaseModel
import json
from llm import swap, handler, transfer

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allows only localhost origin
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
#this is an example menu and in this case I am using berkeley's caffe strada for testing
order = """
Prompt
"""

class UserQuery(BaseModel):
    question: str

@app.post("/answer/")
async def get_answer(query: UserQuery):
    try:
        classification = handler.classify_transaction(query.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    try:
        # Unable to classify
        if classification == 0:
            raise HTTPException(status_code=500, detail=str("Our backend was unable to classify your intent"))
        # Classify as a transfer
        elif classification == 1:
            response = transfer.convert_transfer_intent(query.question)
            query_type = "transfer"
        # Classify as a swap
        elif classification == 2:
            response = swap.convert_transaction(query.question)
            query_type = "swap"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    print(response)
    return {"transaction_type":query_type, "response": response}

@app.post("/swap/")
async def get_swap(query: UserQuery):
    try:
        response = swap.convert_transaction(query.question)
        return {"transaction_type":"swap", response: response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transfer/")
async def get_transfer(query: UserQuery):
    try:
        response = transfer.convert_transfer_intent(query.question)
        return {"transaction_type":"transfer", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/classify/")
async def classify_query(query: UserQuery):
    try:
        response = handler.classify_transaction(query.question)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
