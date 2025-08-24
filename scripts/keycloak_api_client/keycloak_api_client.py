#!/usr/bin/env python3
"""
Script for creating Keycloak clients with "api-" prefix and assigning "codemie" scope and "developer" role
"""

import sys
import json
import requests
from typing import Dict, Any

# ============================================================================
# KEYCLOAK CONFIGURATION
# ============================================================================
KEYCLOAK_CONFIG = {
    'keycloak_server_url': '',
    'codemie_realm': 'codemie-prod',
    'username': 'codemie_provisioner',
    'password': ''
}

# Additional settings
DEFAULT_ROOT_URL = "<codemi_base_url>"
DEFAULT_EMAIL_DOMAIN = "domain.com"
DEFAULT_ACCESS_TOKEN_LIFESPAN = "300"

# ============================================================================


def generate_api_client_name(client_name: str) -> str:
    """
    Generates API client name by adding "api-" prefix to client name

    Args:
        client_name (str): Original client name

    Returns:
        str: API client name with "api-" prefix
    """
    client_name = client_name.strip()

    if client_name.startswith("api-"):
        return client_name

    return f"api-{client_name}"


def parse_project_name(project_name: str) -> tuple[str, str]:
    """
    Parse project name into first_name and last_name
    If single word - duplicate it for both names
    If hyphenated - split by first hyphen

    Args:
        project_name (str): Project name (e.g., "codemie-project" or "test")

    Returns:
        tuple: (first_name, last_name)
    """
    if '-' in project_name:
        parts = project_name.split('-', 1)
        return parts[0], parts[1]
    else:
        return project_name, project_name  # Duplicate single word


def get_keycloak_config() -> Dict[str, str]:
    """
    Returns Keycloak connection configuration

    Returns:
        Dict: Keycloak configuration
    """
    return KEYCLOAK_CONFIG.copy()


def get_admin_token() -> str:
    """
    Gets admin token for working with Keycloak Admin API

    Returns:
        str: Admin access token
    """
    keycloak_config = get_keycloak_config()

    token_url = f"{keycloak_config['keycloak_server_url']}realms/master/protocol/openid-connect/token"

    data = {
        'grant_type': 'password',
        'client_id': 'admin-cli',
        'username': keycloak_config['username'],
        'password': keycloak_config['password']
    }

    response = requests.post(token_url, data=data)
    response.raise_for_status()

    return response.json()['access_token']


def generate_keycloak_client_config(client_name: str, root_url: str = None) -> Dict[str, Any]:
    """
    Generates compatible client configuration for Keycloak

    Args:
        client_name (str): Client name
        root_url (str): Root URL of client (optional)

    Returns:
        Dict: Keycloak client configuration
    """
    api_client_name = generate_api_client_name(client_name)

    if not root_url:
        root_url = DEFAULT_ROOT_URL

    valid_redirect_uris = [f"{root_url}/*"]
    web_origins = [root_url]

    # Minimal compatible configuration
    config = {
        "clientId": api_client_name,
        "name": api_client_name,
        "description": f"API client for {client_name}",
        "enabled": True,
        "alwaysDisplayInConsole": False,

        # Access settings
        "rootUrl": root_url,
        "baseUrl": "",
        "surrogateAuthRequired": False,
        "redirectUris": valid_redirect_uris,
        "webOrigins": web_origins,
        "adminUrl": root_url,

        # Client authentication
        "clientAuthenticatorType": "client-secret",
        "publicClient": False,

        # Authorization settings
        "authorizationServicesEnabled": False,

        # Authentication flow
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": True,

        # Login settings
        "consentRequired": False,

        # Logout settings
        "frontchannelLogout": True,

        # Protocol
        "protocol": "openid-connect",

        # Attributes (only supported ones)
        "attributes": {
            "access.token.lifespan": DEFAULT_ACCESS_TOKEN_LIFESPAN,
            "client_credentials.use_refresh_token": "false",
            "saml.assertion.signature": "false",
            "saml.force.post.binding": "false",
            "saml.multivalued.roles": "false",
            "saml.encrypt": "false",
            "saml.server.signature": "false",
            "exclude.session.state.from.auth.response": "false"
        },

        "fullScopeAllowed": True,
        "nodeReRegistrationTimeout": -1,
        "protocolMappers": [],
        "defaultClientScopes": [
            "web-origins",
            "role_list", 
            "profile",
            "roles",
            "email"
        ],
        "optionalClientScopes": [
            "address",
            "phone",
            "offline_access",
            "microprofile-jwt"
        ]
    }
    
    return config


def client_exists(client_name: str) -> tuple[bool, str]:
    """
    Checks if client exists in Keycloak

    Args:
        client_name (str): Client name

    Returns:
        tuple: (exists: bool, client_id: str)
    """
    try:
        api_client_name = generate_api_client_name(client_name)
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()

        clients_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/clients"

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Get list of clients
        response = requests.get(clients_url, headers=headers, params={'clientId': api_client_name})
        response.raise_for_status()

        clients = response.json()
        if clients:
            return True, clients[0]['id']

        return False, None

    except Exception:
        return False, None


def create_keycloak_client(client_name: str) -> Dict[str, Any]:
    """
    Creates client in Keycloak via Admin API

    Args:
        client_name (str): Client name

    Returns:
        Dict: Client creation result
    """
    try:
        config = generate_keycloak_client_config(client_name)
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()

        clients_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/clients"

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = requests.post(clients_url, headers=headers, json=config)

        if response.status_code == 201:
            location_header = response.headers.get('Location', '')
            client_id = location_header.split('/')[-1] if location_header else None

            return {
                "success": True,
                "message": f"Client '{config['clientId']}' successfully created!",
                "client_id": config['clientId'],
                "internal_id": client_id
            }
        else:
            return {
                "success": False,
                "message": f"Error creating client: {response.status_code}",
                "error": response.text
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "error": str(e)
        }


def update_keycloak_client(client_name: str, internal_client_id: str) -> Dict[str, Any]:
    """
    Updates existing client in Keycloak

    Args:
        client_name (str): Client name
        internal_client_id (str): Internal client ID in Keycloak

    Returns:
        Dict: Client update result
    """
    try:
        config = generate_keycloak_client_config(client_name)
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()

        client_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/clients/{internal_client_id}"

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = requests.put(client_url, headers=headers, json=config)

        if response.status_code == 204:
            return {
                "success": True,
                "message": f"Client '{config['clientId']}' successfully updated!",
                "client_id": config['clientId']
            }
        else:
            return {
                "success": False,
                "message": f"Error updating client: {response.status_code}",
                "error": response.text
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "error": str(e)
        }


def get_client_scope_id(scope_name: str) -> str:
    """
    Gets client scope ID by name

    Args:
        scope_name (str): Scope name

    Returns:
        str: Scope ID or None if not found
    """
    try:
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()

        scopes_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/client-scopes"

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = requests.get(scopes_url, headers=headers)
        response.raise_for_status()

        scopes = response.json()
        for scope in scopes:
            if scope['name'] == scope_name:
                return scope['id']

        return None

    except Exception:
        return None


def assign_client_scope(client_internal_id: str, scope_id: str) -> Dict[str, Any]:
    """
    Assigns client scope to client

    Args:
        client_internal_id (str): Internal client ID
        scope_id (str): Scope ID

    Returns:
        Dict: Assignment result
    """
    try:
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()

        # First get scope information
        scope_info_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/client-scopes/{scope_id}"

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        scope_response = requests.get(scope_info_url, headers=headers)
        scope_response.raise_for_status()
        scope_info = scope_response.json()

        # URL for assigning default scope
        assign_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/clients/{client_internal_id}/default-client-scopes/{scope_id}"

        response = requests.put(assign_url, headers=headers)

        if response.status_code == 204:
            return {
                "success": True,
                "message": f"Client scope '{scope_info['name']}' successfully assigned!"
            }
        else:
            return {
                "success": False,
                "message": f"Error assigning scope: {response.status_code}",
                "error": response.text
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error assigning scope: {str(e)}",
            "error": str(e)
        }


def assign_codemie_scope_to_client(client_internal_id: str) -> Dict[str, Any]:
    """
    Assigns "codemie" scope to client

    Args:
        client_internal_id (str): Internal client ID

    Returns:
        Dict: Assignment result
    """
    scope_id = get_client_scope_id('codemie')

    if not scope_id:
        return {
            "success": False,
            "message": "Client scope 'codemie' not found in Keycloak",
            "error": "SCOPE_NOT_FOUND"
        }

    return assign_client_scope(client_internal_id, scope_id)


def get_role_id(role_name: str) -> str:
    """
    Gets role ID by name

    Args:
        role_name (str): Role name

    Returns:
        str: Role ID or None if not found
    """
    try:
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()

        roles_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/roles"

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = requests.get(roles_url, headers=headers)
        response.raise_for_status()

        roles = response.json()
        for role in roles:
            if role['name'] == role_name:
                return role['id']

        return None

    except Exception:
        return None


def get_client_service_account_user_id(client_internal_id: str) -> str:
    """
    Gets service account user ID for client
    
    Args:
        client_internal_id (str): Internal client ID
        
    Returns:
        str: Service account user ID or None
    """
    try:
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()

        service_account_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/clients/{client_internal_id}/service-account-user"

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = requests.get(service_account_url, headers=headers)
        response.raise_for_status()

        user_info = response.json()
        return user_info.get('id')

    except Exception:
        return None


def assign_role_to_service_account(service_account_user_id: str, role_name: str) -> Dict[str, Any]:
    """
    Assigns role to service account user

    Args:
        service_account_user_id (str): Service account user ID
        role_name (str): Role name

    Returns:
        Dict: Role assignment result
    """
    try:
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()

        # First get role information
        roles_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/roles/{role_name}"

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        role_response = requests.get(roles_url, headers=headers)
        role_response.raise_for_status()
        role_info = role_response.json()

        # Assign role to user
        assign_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/users/{service_account_user_id}/role-mappings/realm"

        role_mapping_data = [role_info]

        response = requests.post(assign_url, headers=headers, json=role_mapping_data)

        if response.status_code == 204:
            return {
                "success": True,
                "message": f"Role '{role_name}' successfully assigned!"
            }
        else:
            return {
                "success": False,
                "message": f"Error assigning role: {response.status_code}",
                "error": response.text
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error assigning role: {str(e)}",
            "error": str(e)
        }


def assign_developer_role_to_client(client_internal_id: str) -> Dict[str, Any]:
    """
    Assigns "developer" role to client's service account

    Args:
        client_internal_id (str): Internal client ID

    Returns:
        Dict: Role assignment result
    """
    # Get service account user for client
    service_account_user_id = get_client_service_account_user_id(client_internal_id)

    if not service_account_user_id:
        return {
            "success": False,
            "message": "Service account user not found for client",
            "error": "SERVICE_ACCOUNT_NOT_FOUND"
        }

    # Assign role
    return assign_role_to_service_account(service_account_user_id, 'developer')


def update_service_account_user_details(client_internal_id: str, project_name: str) -> Dict[str, Any]:
    """
    Updates service account user details for client

    Args:
        client_internal_id (str): Internal client ID
        project_name (str): Project name

    Returns:
        Dict: User details update result
    """
    try:
        # Get service account user
        service_account_user_id = get_client_service_account_user_id(client_internal_id)

        if not service_account_user_id:
            return {
                "success": False,
                "message": "Service account user not found for client",
                "error": "SERVICE_ACCOUNT_NOT_FOUND"
            }

        # Form data according to template
        api_client_name = generate_api_client_name(project_name)
        first_name, last_name = parse_project_name(project_name)

        user_data = {
            "email": f"service-account-{api_client_name}@{DEFAULT_EMAIL_DOMAIN}",
            "firstName": first_name,
            "lastName": last_name,
            "emailVerified": True
        }

        # Update user data
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()

        user_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/users/{service_account_user_id}"

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = requests.put(user_url, headers=headers, json=user_data)

        if response.status_code == 204:
            return {
                "success": True,
                "message": "Service account user details updated!",
                "details": {
                    "email": user_data["email"],
                    "firstName": user_data["firstName"],
                    "lastName": user_data["lastName"]
                }
            }
        else:
            return {
                "success": False,
                "message": f"Error updating user details: {response.status_code}",
                "error": response.text
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error updating user details: {str(e)}",
            "error": str(e)
        }


def update_service_account_user_attributes(client_internal_id: str, project_name: str) -> Dict[str, Any]:
    """
    Updates service account user attributes for client

    Args:
        client_internal_id (str): Internal client ID
        project_name (str): Project name (without api- prefix)

    Returns:
        Dict: User attributes update result
    """
    try:
        # Get service account user
        service_account_user_id = get_client_service_account_user_id(client_internal_id)

        if not service_account_user_id:
            return {
                "success": False,
                "message": "Service account user not found for client",
                "error": "SERVICE_ACCOUNT_NOT_FOUND"
            }

        # Form attributes according to screenshot example
        # applications = codemie-project
        # applications_admin = codemie-project
        user_attributes = {
            "applications": [project_name],
            "applications_admin": [project_name]
        }

        # First get current user data
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()

        user_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/users/{service_account_user_id}"

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Get current user
        get_response = requests.get(user_url, headers=headers)
        get_response.raise_for_status()
        current_user_data = get_response.json()

        # Update only attributes
        current_user_data['attributes'] = user_attributes

        # Update user
        response = requests.put(user_url, headers=headers, json=current_user_data)

        if response.status_code == 204:
            return {
                "success": True,
                "message": "Service account user attributes updated!",
                "attributes": {
                    "applications": project_name,
                    "applications_admin": project_name
                }
            }
        else:
            return {
                "success": False,
                "message": f"Error updating user attributes: {response.status_code}",
                "error": response.text
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error updating user attributes: {str(e)}",
            "error": str(e)
        }


def get_client_secret(client_internal_id: str) -> str:
    """
    Gets client secret from Keycloak

    Args:
        client_internal_id (str): Internal client ID

    Returns:
        str: Client secret or None if not found
    """
    try:
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()

        secret_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/clients/{client_internal_id}/client-secret"

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = requests.get(secret_url, headers=headers)
        response.raise_for_status()

        secret_data = response.json()
        return secret_data.get('value')

    except Exception:
        return None


def process_client(client_name: str) -> None:
    """
    Main function for processing client:
    - Creates or updates client
    - Assigns "codemie" scope
    - Assigns "developer" role
    - Updates service account user details
    - Adds applications and applications_admin attributes
    - Shows client details with secret

    Args:
        client_name (str): Project name
    """
    api_client_name = generate_api_client_name(client_name)

    print(f"Processing client '{api_client_name}'...")

    # Check if client exists
    exists, client_internal_id = client_exists(client_name)

    if exists:
        print(f"Client '{api_client_name}' already exists. Updating...")
        result = update_keycloak_client(client_name, client_internal_id)
    else:
        print(f"Creating new client '{api_client_name}'...")
        result = create_keycloak_client(client_name)
        if result["success"] and result.get("internal_id"):
            client_internal_id = result["internal_id"]

    # Output create/update result
    if result["success"]:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ {result['message']}")
        if result.get('error'):
            print(f"Details: {result['error']}")
        return

    # Assign "codemie" scope
    if client_internal_id:
        print("Assigning client scope 'codemie'...")
        scope_result = assign_codemie_scope_to_client(client_internal_id)

        if scope_result["success"]:
            print(f"✅ {scope_result['message']}")
        else:
            print(f"⚠️ {scope_result['message']}")

    # Assign "developer" role
    if client_internal_id:
        print("Assigning role 'developer'...")
        role_result = assign_developer_role_to_client(client_internal_id)

        if role_result["success"]:
            print(f"✅ {role_result['message']}")
        else:
            print(f"⚠️ {role_result['message']}")

    # Update service account user details
    if client_internal_id:
        print("Updating service account user details...")
        user_result = update_service_account_user_details(client_internal_id, client_name)

        if user_result["success"]:
            print(f"✅ {user_result['message']}")
            if user_result.get('details'):
                details = user_result['details']
                print(f"   - Email: {details['email']}")
                print(f"   - First name: {details['firstName']}")
                print(f"   - Last name: {details['lastName']}")
        else:
            print(f"⚠️ {user_result['message']}")

    # Add applications and applications_admin attributes
    if client_internal_id:
        print("Adding user attributes...")
        attr_result = update_service_account_user_attributes(client_internal_id, client_name)

        if attr_result["success"]:
            print(f"✅ {attr_result['message']}")
            if attr_result.get('attributes'):
                attributes = attr_result['attributes']
                print(f"   - applications: {attributes['applications']}")
                print(f"   - applications_admin: {attributes['applications_admin']}")
        else:
            print(f"⚠️ {attr_result['message']}")

    # Get and display client secret
    if client_internal_id:
        client_secret = get_client_secret(client_internal_id)

        print(f"📋 Client Details:")
        print(f"   - Client ID: {api_client_name}")

        if client_secret:
            print(f"   - Client Secret: {client_secret}")
        else:
            print(f"   - Client Secret: ⚠️ Could not retrieve secret")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 keycloak_api_client.py <project_name>")
        print("Example: python3 keycloak_api_client.py codemie-project")
        print()
        print("Script automatically:")
        print("  • Creates client 'api-<project_name>' (if doesn't exist)")
        print("  • Updates client (if already exists)")
        print("  • Assigns client scope 'codemie'")
        print("  • Assigns role 'developer'")
        print("  • Updates service account user details")
        print("  • Adds 'applications' and 'applications_admin' attributes")
        print("  • Shows client ID and secret")
        sys.exit(1)

    client_name = sys.argv[1]
    process_client(client_name)


if __name__ == "__main__":
    main()
