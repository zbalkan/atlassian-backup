import os
import yaml


def create_config() -> None:
    atlassian_tenant: str = input("What is your Atlassian tenant name? ")
    user: str = input("What is your Atlassian cloud account email address? ")
    password: str = input("Paste your Atlassian API token: ")
    attachments: str = input(
        "Do you want to include attachments? (true / false) ")
    custom_config: dict[str, str] = {
        'ATLASSIAN_TENANT': atlassian_tenant,
        'INCLUDE_ATTACHMENTS': attachments.lower(),
        'ATLASSIAN_EMAIL': user,
        'API_TOKEN': password
    }

    config_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'config.yaml')
    with open(config_path, 'w+') as config_file:
        yaml.dump(custom_config, config_file)
