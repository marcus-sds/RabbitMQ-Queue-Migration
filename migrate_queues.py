import argparse
import os
import subprocess
import requests
from requests.auth import HTTPBasicAuth

# Configuration
rabbit_url = "http://localhost:15672"
auth = HTTPBasicAuth(os.getenv('USERNAME'), os.getenv('PASSWD'))
DRYRUN = False

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

def get_vhosts():
    arr_vhosts = []
    dict_vhosts = {}
    response = requests.get(f"{rabbit_url}/api/vhosts", auth=auth)
    if response.status_code == 200:
        vhosts = response.json()
        for vhost in vhosts:
            arr_vhosts.append(vhost['name'])
            dict_vhosts[vhost['name']] = vhost
    return arr_vhosts, dict_vhosts
def vhost_apireplace(vhost_name):
    if vhost_name == "/":
        vhost_name = "%2F
    else:
        vhost_name = vhost_name.replace("/","")
    return vhost_name
    
def put_vhosts_default_quorum(vhost_name_api, vhost):
    vhost["default_queue_type"] = "quorum"
    create_response = requests.put(f"{rabbit_url}/api/vhosts/{vhost_name_api}", auth=auth, json=vhost)
    printf(f"updating default Queue to quorum with {vhost_name}")

def migrate_queue(queue_name, vhost_name_api):
    """Migrate a single queue to a Quorum Queue."""
    response = requests.get(f"{rabbit_url}/api/queues/{vhost_name_api}/{queue_name}", auth=auth)
    if response.status_code != 200:
        print(f"{vhost_name_api} Queue {queue_name} does not exist or cannot be retrieved.")
        return

    queue = response.json()
    name = queue['name']
    vhost = queue['vhost']
    features = queue.get('arguments', {})
    if features.get('x-queue-type') == 'quorum':
        print(f"  - skipping x-queue-type=quorum with {name} features")
        return
    if features.get('x-max-priority'):
        del features['x-max-priority']
        print(f"  - x-max-priority removed from {name} features")
    if features.get('x-queue-mode'):
        del features['x-queue-mode']
        print(f"  - x-queue-mode removed from {name} features")
    print(f"{vhost_name_api} Migrating queue: {name} in vhost: {vhost} with features: {features}")

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

    if not DRYRUN:
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
        printf(f"creating Quorum Queue {name} with {data}")
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
            printf(f"Binding Quorum Queue {name} to {source} with {bind_data}")
            if bind_response.status_code == 201:
                print(f"Successfully re-bound {name} to exchange {source} with routing key {routing_key}.")
            else:
                print(f"Failed to re-bind {name} to exchange {source}. Error: {bind_response.text}")

def main():
    parser = argparse.ArgumentParser(description="Migrate RabbitMQ queues from Classic to Quorum.")
    parser.add_argument("--queues", nargs="*", help="Specific queues to migrate. If not specified, all queues will be migrated.")
    parser.add_argument("--backup", action="store_true", help="Backup RabbitMQ configuration before migrating.")
    parser.add_argument("--dryrun", action="store_true", help="View only when argument is passed")
    args = parser.parse_args()

    global DRYRUN
    DRYUN = args.dryrun

    arr_vhosts, dict_vhosts = get_vhosts()
    if args.backup:
        backup_definitions()

    if args.queues:
        for queue in args.queues:
            migrate_queue(queue)
    else:
        for vhost_name in arr_vhosts:
            put_vhosts_default_quorum(vhost_name, dict_vhosts[vhost_name])
            vhost_name_api = vhost_apireplace(vhost_name)
            queues_response = requests.get(f"{rabbit_url}/api/queues/{vhost_name_api}", auth=auth)
            if queues_response.status_code != 200:
                print("Failed to retrieve queues.")
                exit(1)
    
            all_queues = queues_response.json()
            for queue in all_queues:
                migrate_queue(queue["name"], vhost_name_api)

if __name__ == "__main__":
    main()
