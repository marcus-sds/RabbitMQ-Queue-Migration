import argparse
import os
import subprocess
import requests
from requests.auth import HTTPBasicAuth

# Configuration
rabbit_url = "http://localhost:15672"
auth = HTTPBasicAuth("username", "password")

def backup_definitions():
    """Back up the current RabbitMQ configuration."""
    backup_file = "/tmp/backup.json"
    try:
        print(f"Backing up RabbitMQ configuration to {backup_file}...")
        subprocess.run(
            ["rabbitmqctl", "export_definitions", backup_file],
            check=True,
        )
        print(f"Backup completed successfully: {backup_file}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to create backup. Error: {e}")
        exit(1)

def migrate_queue(queue_name):
    """Migrate a single queue to a Quorum Queue."""
    response = requests.get(f"{rabbit_url}/api/queues/%2F/{queue_name}", auth=auth)
    if response.status_code != 200:
        print(f"Queue {queue_name} does not exist or cannot be retrieved.")
        return

    queue = response.json()
    name = queue['name']
    vhost = queue['vhost']
    features = queue.get('arguments', {})
    print(f"Migrating queue: {name} in vhost: {vhost} with features: {features}")

    all_bindings = requests.get(f"{rabbit_url}/api/bindings/%2F", auth=auth).json()
    bindings = [
        binding for binding in all_bindings
        if binding.get("destination") == name and binding.get("destination_type") == "queue"
    ]

    if bindings:
        print(f"Found bindings for {name}:")
        for binding in bindings:
            exchange = binding.get('source', 'Unknown Exchange')
            routing_key = binding.get('routing_key', 'No routing key')
            print(f"  - From Exchange: {exchange} with Routing Key: {routing_key}")

    delete_response = requests.delete(f"{rabbit_url}/api/queues/%2F/{name}", auth=auth)
    if delete_response.status_code == 204:
        print(f"Successfully deleted the Classic Queue: {name}")
    else:
        print(f"Failed to delete the Classic Queue: {name}. Error: {delete_response.text}")
        return

    features['x-queue-type'] = 'quorum'
    data = {
        "durable": True,
        "arguments": features
    }
    create_response = requests.put(f"{rabbit_url}/api/queues/%2F/{name}", auth=auth, json=data)
    if create_response.status_code == 201:
        print(f"Successfully created Quorum Queue: {name}")
    else:
        print(f"Failed to create Quorum Queue: {name}. Error: {create_response.text}")
        return

    for binding in bindings:
        source = binding['source']
        routing_key = binding['routing_key']
        bind_data = {"routing_key": routing_key, "arguments": binding.get('arguments', {})}
        bind_response = requests.post(f"{rabbit_url}/api/bindings/%2F/e/{source}/q/{name}", auth=auth, json=bind_data)
        if bind_response.status_code == 201:
            print(f"Successfully re-bound {name} to exchange {source} with routing key {routing_key}.")
        else:
            print(f"Failed to re-bind {name} to exchange {source}. Error: {bind_response.text}")

def main():
    parser = argparse.ArgumentParser(description="Migrate RabbitMQ queues from Classic to Quorum.")
    parser.add_argument("--queues", nargs="*", help="Specific queues to migrate. If not specified, all queues will be migrated.")
    parser.add_argument("--backup", action="store_true", help="Backup RabbitMQ configuration before migrating.")
    args = parser.parse_args()

    if args.backup:
        backup_definitions()

    if args.queues:
        for queue in args.queues:
            migrate_queue(queue)
    else:
        queues_response = requests.get(f"{rabbit_url}/api/queues/%2F", auth=auth)
        if queues_response.status_code != 200:
            print("Failed to retrieve queues.")
            exit(1)

        all_queues = queues_response.json()
        for queue in all_queues:
            migrate_queue(queue["name"])

if __name__ == "__main__":
    main()
