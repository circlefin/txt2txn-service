import requests
import json
import csv

# assuming you're running the backend locally
endpoint = "http://127.0.0.1:8000/answer"
test_cases_path = "./test_cases.csv"
max_retries = 3

headers = {"Content-Type": "application/json"}
csv_reader = csv.DictReader(open(test_cases_path, newline=''))

num_correct = 0
row_num = 0
failed_requests = 0
print("Trying test cases!")
for test_case in csv_reader:
    prompt =  test_case["Prompt"]
    attempt = 1
    while attempt < max_retries:
        response = requests.post(endpoint, headers=headers, json={ "question": test_case["Prompt"]})
        if response.status_code != 200:
            print("Bad request: ", response.status_code)
            print(prompt)
            attempt += 1
        else:
            break
    if attempt > max_retries:
        print("Failed request")
        failed_requests += 1
    intent = response.json()
    expected_intent = json.loads(test_case["Expected Intent"])
    if intent == expected_intent:
        num_correct += 1
    else:
        print("Failed to correctly parse intent!")
        print("Prompt:")
        print(prompt)
        print("Parsed Intent:")
        print(intent)
        print("Expected Intent:")
        print(expected_intent)
    row_num += 1

print("Failed requests: ", failed_requests)
print("Test cases: ", row_num)
print("Percent Correct: ", (num_correct / row_num) * 100, "%")
