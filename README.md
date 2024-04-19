# TXT2TXN Backend

This repo serves as the backend for the TXT2TXN project.

TXT2TXN is a collaboration between Circle and Blockchain at Berkeley, in particular [Niall Mandal](https://github.com/niallmandal).

## Setup 

1. Set up virtual python environment.
```sh
python3 -m venv venv
```

2. Activate virtual environment.
```sh
source venv/bin/activate
```

3. Install dependencies.
```
pip install -r requirements.txt
```

4. Create and populate a .env file.
```
cp .env.example .env
```
Then add OpenAI key to .env file 

## Build
Execute the following to run the service:
```
uvicorn main:app --reload
```
