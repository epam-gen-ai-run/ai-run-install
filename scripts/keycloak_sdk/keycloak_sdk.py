#!/usr/bin/env python3
"""
Script for creating Keycloak client with name "codemie-sdk"
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
DEFAULT_ACCESS_TOKEN_LIFESPAN = "300"

# ============================================================================


def generate_sdk_client_name() -> str:
    """
    Generates SDK client name (always returns "codemie-sdk")
    
    Returns:
        str: Always returns "codemie-sdk"
    """
    return "codemie-sdk"


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


def generate_keycloak_client_config(root_url: str = None) -> Dict[str, Any]:
    """
    Generates compatible client configuration for Keycloak SDK client
    
    Args:
        root_url (str): Root URL of client (optional)

    Returns:
        Dict: Keycloak client configuration
    """
    sdk_client_name = generate_sdk_client_name()
    
    if not root_url:
        root_url = DEFAULT_ROOT_URL
    
    valid_redirect_uris = [f"{root_url}/*"]
    web_origins = [root_url]
    
    # SDK client configuration based on the screenshot
    config = {
        "clientId": sdk_client_name,
        "name": "CodeMie SDK",
        "description": "CodeMie SDK",
        "enabled": True,
        "alwaysDisplayInConsole": False,
        
        # Access settings
        "rootUrl": root_url,
        "baseUrl": "",
        "surrogateAuthRequired": False,
        "redirectUris": valid_redirect_uris,
        "webOrigins": web_origins,
        "adminUrl": root_url,
        
        # Client authentication - OFF (public client)
        "clientAuthenticatorType": "client-secret",
        "publicClient": True,  # This makes it a public client (no authentication required)
        
        # Authorization settings - OFF
        "authorizationServicesEnabled": False,
        
        # Authentication flow
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,  # OFF as shown in screenshot
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": False,  # OFF as shown in screenshot
        
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


def client_exists() -> tuple[bool, str]:
    """
    Checks if SDK client exists in Keycloak
        
    Returns:
        tuple: (exists: bool, client_id: str)
    """
    try:
        sdk_client_name = generate_sdk_client_name()
        keycloak_config = get_keycloak_config()
        admin_token = get_admin_token()
        
        clients_url = f"{keycloak_config['keycloak_server_url']}admin/realms/{keycloak_config['codemie_realm']}/clients"
        
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
        
        # Get list of clients
        response = requests.get(clients_url, headers=headers, params={'clientId': sdk_client_name})
        response.raise_for_status()
        
        clients = response.json()
        if clients:
            return True, clients[0]['id']
        
        return False, None
        
    except Exception:
        return False, None


def create_keycloak_client() -> Dict[str, Any]:
    """
    Creates SDK client in Keycloak via Admin API

    Returns:
        Dict: Client creation result
    """
    try:
        config = generate_keycloak_client_config()
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


def update_keycloak_client(internal_client_id: str) -> Dict[str, Any]:
    """
    Updates existing SDK client in Keycloak
    
    Args:
        internal_client_id (str): Internal client ID in Keycloak

    Returns:
        Dict: Client update result
    """
    try:
        config = generate_keycloak_client_config()
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


def process_client() -> None:
    """
    Main function for processing SDK client:
    - Creates or updates client "codemie-sdk"
    - Assigns "codemie" scope
    - Shows client details (no secret for public client)
    """
    sdk_client_name = generate_sdk_client_name()
    
    print(f"Processing SDK client '{sdk_client_name}'...")
    
    # Check if client exists
    exists, client_internal_id = client_exists()
    
    if exists:
        print(f"Client '{sdk_client_name}' already exists. Updating...")
        result = update_keycloak_client(client_internal_id)
    else:
        print(f"Creating new client '{sdk_client_name}'...")
        result = create_keycloak_client()
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
    
    # Display client details
    print(f"📋 SDK Client Details:")
    print(f"   - Client ID: {sdk_client_name}")
    print(f"   - Name: CodeMie SDK")
    print(f"   - Description: CodeMie SDK")
    print(f"   - Type: Public Client (no secret required)")
    print(f"   - Root URL: {DEFAULT_ROOT_URL}")
    print(f"   - Valid Redirect URIs: {DEFAULT_ROOT_URL}/*")
    print(f"   - Web Origins: {DEFAULT_ROOT_URL}")


def main():
    print("Keycloak SDK Client Creator")
    print("=" * 50)
    print()
    print("This script will automatically:")
    print("  • Create client 'codemie-sdk' (if doesn't exist)")
    print("  • Update client (if already exists)")  
    print("  • Assign client scope 'codemie'")
    print("  • Configure as public client (no authentication required)")
    print("  • Show client details")
    print()
    
    process_client()


if __name__ == "__main__":
    main()