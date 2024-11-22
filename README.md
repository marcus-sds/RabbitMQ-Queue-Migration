# RabbitMQ Queue Migration Script

This Python script is designed to migrate RabbitMQ queues from classic to quorum queues. It offers the ability to migrate all queues or specific queues provided via command-line arguments. Additionally, the script includes an option to back up the current RabbitMQ configuration before performing any migrations.

*This script is designed to simplify the migration process and ensure data consistency during the transition to quorum queues. Use it carefully and ensure backups are made before making significant changes.*

## Features

1. Migrate all RabbitMQ queues to quorum queues.
2. Migrate specific queues provided via the command line.
3. Recreate queue bindings to ensure seamless operation after migration.
4. Optionally create a backup of the current RabbitMQ configuration before migration using the `rabbitmqctl export_definitions` command.

## Prerequisites

1. **Python**: Ensure Python 3.x is installed on the server running the script.
2. **RabbitMQ Management Plugin**: The RabbitMQ Management API must be enabled (`rabbitmq-plugins enable rabbitmq_management`).
3. **RabbitMQ CLI Access**: The `rabbitmqctl` command must be installed and accessible on the server.
4. **Host Configuration**: The RabbitMQ node must be specified in the `/etc/hosts# RabbitMQ Queue Migration Script

This Python script is designed to migrate RabbitMQ queues from classic to quorum queues. It offers the ability to migrate all queues or specific queues provided via command-line arguments. Additionally, the script includes an option to back up the current RabbitMQ configuration before performing any migrations.

## Dependencies 
The script uses the following Python libraries:

- *argparse*: For handling command-line arguments.
- *requests*: For interacting with RabbitMQ Management API.
- *subprocess*: For executing RabbitMQ CLI commands.

To install the required libraries, run:

```
pip3 install requests
```


## Configuration

Update the following configuration in the script:

- **rabbitmq_url**: The URL of the RabbitMQ Management API. Default is *http://localhost:15672*.
- **auth**: Replace with your RabbitMQ credentials (username and password).

## Usage

- Migrate All Queues (No Backup Kept)

    ```python
    python3 migrate_queues.py
    ```

- Migrate Specific Queues (No Backup Kept)

    ```
    python3 migrate_queues.py --queues queue1 queue2
    ```

- Migrate All Queues with Backup 
  
  ```
  python3 migrate_queues.py --backup
  ```

- Migrate Specific Queues with Backup
  
  ```
  python3 migrate_queues.py --queues queue1 queue2 --backup
  ```

### How It Works
If the --backup flag is provided, the script runs:
```
rabbitmqctl export_definitions /tmp/backup.json
```
This creates a backup of the current RabbitMQ configuration in /tmp/backup.json.

The script retrieves the list of queues from RabbitMQ Management API. If specific queues are provided via the --queues argument, only those are migrated.

For each queue:

- The script fetches its configuration and bindings.
- Deletes the classic queue.
- Creates a new quorum queue with the same configuration.
- Recreates the bindings for the new quorum queue.
- Migration progress and errors are printed to the console.

## Notes

- The backup file (/tmp/backup.json) is overwritten each time the script runs with the --backup flag.
- Make sure RabbitMQ is running and accessible at the configured rabbit_url (http://localhost:15672) with appropriate credentials.
- The RabbitMQ node specified in /etc/hosts must match the actual node hostname.

## Troubleshooting 

- **Connection Errors**:

  - Ensure RabbitMQ is running and the management API is enabled.
  - Verify the RabbitMQ node is specified correctly in */etc/hosts*.

- **Permission Denied**:

  - Ensure the user has necessary permissions to access the RabbitMQ Management API and execute rabbitmqctl commands.

- **Backup Fails**:

  - Ensure *rabbitmqctl* is installed and accessible in the system's *PATH*.
  - Verify the RabbitMQ node is correctly specified in */etc/hosts*.
