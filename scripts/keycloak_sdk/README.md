# Keycloak API Client Creator

## 📝 Description

This script is designed to automate SDK client creation in Keycloak.

**Script Purpose:**
- Automatic SDK client creation in Keycloak "codemie-sdk"
- Assigning "codemie" client scope for proper authorization

## 🔧 Prerequisites

Before using the script, you need to prepare Keycloak:

### 1. Creating Service User `codemie_provisioner`

1. Log in to Keycloak Admin Console
2. Select "Master" realm in the left upper corner
3. Navigate to Users → Add user
4. Create user with username `codemie_provisioner`
5. Set password in Credentials section (disable Temporary)
6. Assign the following role mappings:

   Steps for user creation:
   1. Select "Master" realm in the left upper corner of keycloak page
   2. Select Users tab
   3. Click "Add user" button
   4. Set username "codemie_provisioner"
   5. Click on created user and choose "Credentials" tab
   6. Set password and disable temporary radio button
   7. Click "Role mapping" tab and click "Assign role" button
   8. Select filter by clients and add mappings:

      ```
      default-roles-master
      codemie-prod-realm manage-events
      codemie-prod-realm view-events
      codemie-prod-realm query-clients
      codemie-prod-realm manage-users
      codemie-prod-realm view-clients
      codemie-prod-realm manage-clients
      codemie-prod-realm view-users
      codemie-prod-realm create-client
      codemie-prod-realm manage-realm
      codemie-prod-realm manage-identity-providers
      codemie-prod-realm impersonation
      codemie-prod-realm view-authorization
      codemie-prod-realm query-groups
      codemie-prod-realm view-identity-providers
      codemie-prod-realm query-realms
      codemie-prod-realm view-realm
      codemie-prod-realm query-users
      codemie-prod-realm manage-authorization
      ```

### 2. Realm Configuration

Ensure the `codemie-prod` realm is configured in Keycloak with:
- **"codemie" client scope** - custom scope for API access

### 3. Required Keycloak Objects

The script expects the following objects to exist in the `codemie-prod` realm:
- **Client Scope**: `codemie` - for API authorization

## 🎯 Functionality

The script manages API clients in the `codemie-prod` Keycloak realm:

For each client, the following operations are performed:
1. ✅ Generate API client name "codemie-sdk"
2. ✅ Create new client or update existing one
3. ✅ Assign "codemie" client scope for proper API authorization

## 🚀 Usage

### Creating or updating API client

```bash
python3 keycloak_sdk
```

### Examples

```bash
python3 keycloak_sdk
```

## 📋 Client Configuration Details

### Generated Client Settings:
- **Client ID**: `codemie-sdk`
- **Name**: `codemie-sdk`
- **Description**: `codemie-sdk`
- **Standard Flow**: Enabled
- **Direct Access Grants**: Enabled
- **Service Accounts**: Disabled
- **Root URL**: `<codemi_base_url>`
- **Valid Redirect URIs**: `<codemi_base_url>/*`
- **Access Token Lifespan**: `300` seconds

### Client Scopes:
- **Default Scopes**: `web-origins`, `role_list`, `profile`, `roles`, `email`, `codemie`
- **Optional Scopes**: `address`, `phone`, `offline_access`, `microprofile-jwt`

## ⚙️ Configuration

Keycloak connection settings are located in the `keycloak_sdk.py` file:

```python
KEYCLOAK_CONFIG = {
    'keycloak_server_url': '',
    'codemie_realm': 'codemie-prod',
    'username': 'codemie_provisioner',
    'password': ''
}

# Additional settings
DEFAULT_ROOT_URL = "<codemi_base_url>"
DEFAULT_ACCESS_TOKEN_LIFESPAN = "300"
```

**Important:** Set `keycloak_server_url` and `password` in script configuration before using.

## 🔧 Script Workflow

The script execution flow:

```
Keycloak SDK Client Creator
==================================================

This script will automatically:
  • Create client 'codemie-sdk' (if doesn't exist)
  • Update client (if already exists)
  • Assign client scope 'codemie'
  • Configure as public client (no authentication required)
  • Show client details

Processing SDK client 'codemie-sdk'...
Creating new client 'codemie-sdk'...
✅ Client 'codemie-sdk' successfully created!
Assigning client scope 'codemie'...
✅ Client scope 'codemie' successfully assigned!
📋 SDK Client Details:
   - Client ID: codemie-sdk
   - Name: CodeMie SDK
   - Description: CodeMie SDK
   - Type: Public Client (no secret required)
   - Root URL: <codemi_base_url>
   - Valid Redirect URIs: <codemi_base_url>/*
   - Web Origins: <codemi_base_url>
```

## 📁 File Structure

- `keycloak_sdk.py` - Main script
- `README.md` - Documentation
