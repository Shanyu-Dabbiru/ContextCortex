import sys
import os
import requests
import argparse
from dotenv import load_dotenv

# Load .env from root
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
dotenv_path = os.path.join(root_dir, ".env.agent")
load_dotenv(dotenv_path)

INGESTION_SERVICE_URL = os.environ.get("INGESTION_SERVICE_URL", "http://localhost:8011")

def ingest_message(user, text, thread_id):
    url = f"{INGESTION_SERVICE_URL}/api/v1/ingest_message"
    payload = {"user": user, "text": text, "thread_id": thread_id}
    resp = requests.post(url, json=payload)
    print(f"Response: {resp.status_code} - {resp.json()}")

def simulate_pr(author, diff_file, pr_number):
    if not os.path.exists(diff_file):
        print(f"Error: File {diff_file} not found")
        return

    with open(diff_file, "r") as f:
        code_diff = f.read()

    # Heuristic for file paths from diff
    file_paths = []
    for line in code_diff.split("\n"):
        if line.startswith("+++ b/"):
            file_paths.append(line[6:])

    url = f"{INGESTION_SERVICE_URL}/api/v1/simulate_pr"
    payload = {
        "author": author,
        "code_diff": code_diff,
        "file_paths": file_paths,
        "pr_number": pr_number
    }
    resp = requests.post(url, json=payload)
    print(f"Response: {resp.status_code} - {resp.json()}")

def main():
    parser = argparse.ArgumentParser(description="ContextCortex CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Message command
    msg_parser = subparsers.add_parser("message", help="Simulate a message ingestion")
    msg_parser.add_argument("--user", required=True)
    msg_parser.add_argument("--text", required=True)
    msg_parser.add_argument("--thread", default="thread-1")

    # PR command
    pr_parser = subparsers.add_parser("pr", help="Simulate a PR ingestion")
    pr_parser.add_argument("--author", required=True)
    pr_parser.add_argument("--diff", required=True, help="Path to a diff file")
    pr_parser.add_argument("--number", type=int, default=1)

    args = parser.parse_args()

    if args.command == "message":
        ingest_message(args.user, args.text, args.thread)
    elif args.command == "pr":
        simulate_pr(args.author, args.diff, args.number)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
