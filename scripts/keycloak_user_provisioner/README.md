# Keycloak User Provisioner

Automated user creation in Keycloak with Identity Provider Links setup between realms.

## 🎯 Functionality

The script manage users in two Keycloak realms:
- **broker** (broker realm)
- **codemie-prod** (main realm)

For each user, the following is performed:
1. ✅ Name to email conversion: `"Jon Doe"` → `"jon_doe@domain.com"`
2. ✅ User creation in both realms
3. ✅ Identity Provider Link setup between realms
4. ✅ Assign `developer` role in `codemie-prod` realm
5. ✅ Add `applications` attribute with email and project

## 📦 Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## 🚀 Usage

### 1. Creating a single user

```bash
python3 keycloak_user_provisioner.py my-project "Jon Doe"
```

### 2. Creating multiple users

```bash
python3 keycloak_user_provisioner.py my-project "Jon Doe, John Smith, Jane Doe"
```

### 3. Example with domain

```bash
python3 keycloak_user_provisioner.py my-project "Jon Doe, John Smith, Jane Doe" @domain.com
```


## 📋 Example Results

### User in `broker` realm:
- **Username**: `jon_doe@domain.com`
- **Email**: `jon_doe@domain.com`
- **First Name**: `Jon`
- **Last Name**: `Doe`
- **Enabled**: `true`
- **Email Verified**: `false`

### Identity Provider Link:
- **Provider**: `IDP`
- **Type**: `Custom`
- **User ID**: `jon_doe@domain.com`
- **Username**: `jon_doe@domain.com`

### User in `codemie-prod` realm:
- **Username**: `jon_doe@domain.com`
- **Email**: `jon_doe@domain.com`
- **First Name**: `Jon`
- **Last Name**: `Doe`
- **Enabled**: `true`
- **Email Verified**: `false`
- **Role**: `developer`
- **Attributes**:
  - `applications`: `"jon_doe@domain.com,my-project"`

### Identity Provider Link:
- **Provider**: `Broker`
- **Type**: `Custom`
- **User ID**: `39b2fa6c-5d9d-491a-a945-ec79fa3c8627` (ID from broker)
- **Username**: `jon_doe@domain.com`

## ⚙️ Configuration

Keycloak connection settings are located in the `keycloak_user_provisioner.py` file:

```python
class KeycloakUserProvisioner:
    def __init__(self, email_domain='@domain.com'):
        self.config = {
            'keycloak_server_url': '',
            'master_realm': 'master',
            'broker_realm': 'master',
            'codemie_realm': 'codemie-prod',
            'client_id': 'admin-cli',
            'username': 'codemie_provisioner',
            'password': ''
        }
        self.email_domain = email_domain
        self.access_token = None
        self.token_expires_at = None
        self.session = requests.Session()
```

How to create codemie_provisioner user:

1. Select "Master" realm in the left upper corner of keycloak page

2. Select Users tab

3. Click create Add user button

4. Set username "codemie_provisioner"

5. Click on created user and choose "Credentials" tab

6. Set password and disable temporary radio button

7. Click "Role" mapping tab and click "Assign role" button

8. Select filter by clients and add mappings:

   default-roles-master
   codemie-prod-realmmanage-events
   codemie-prod-realmview-events
   codemie-prod-realmquery-clients
   codemie-prod-realmmanage-users
   codemie-prod-realmview-clients
   codemie-prod-realmmanage-clients
   codemie-prod-realmview-users
   codemie-prod-realmcreate-client
   codemie-prod-realmmanage-realm
   codemie-prod-realmmanage-identity-providers
   codemie-prod-realmimpersonation
   codemie-prod-realmview-authorization
   codemie-prod-realmquery-groups
   codemie-prod-realmview-identity-providers
   codemie-prod-realmquery-realms
   codemie-prod-realmview-realm
   codemie-prod-realmquery-users
   codemie-prod-realmmanage-authorization
   broker-realmview-identity-providers
   broker-realmmanage-users
   broker-realmquery-groups
   broker-realmquery-users

9. Set login and password in script credentials.

## 🔧 Additional Features

### Working with existing users

The script intelligently handles existing users:

- **New user**: created with `applications = "email,project"` attribute
- **Existing user**: project is added to attribute if not present

Example attribute progression:
1. First project: `"jon_doe@domain.com,my-project"`
2. Second project: `"jon_doe@domain.com,my-project,new-project"`
3. Third project: `"jon_doe@domain.com,my-project,new-project,another-project"`

### Logging

The script provides detailed logging:

```
🚀 Starting user provisioning: 'Jon Doe' for project 'my-project'
================================================================================
📧 Email: jon_doe@domain.com
👤 First Name: Jon
👤 Last Name: Doe
📁 Project: my-project
--------------------------------------------------------------------------------
🔐 Authenticating in realm 'broker'...
✅ Successful authentication in realm 'broker'
👤 Creating user 'jon_doe@domain.com' in realm 'broker'...
✅ User 'jon_doe@domain.com' successfully created in realm 'broker' with ID: 39b2fa6c-5d9d-491a-a945-ec79fa3c8627
🔐 Authenticating in realm 'codemie-prod'...
✅ Successful authentication in realm 'codemie-prod'
👤 Creating user 'jon_doe@domain.com' in realm 'codemie-prod'...
✅ User 'jon_doe@domain.com' successfully created in realm 'codemie-prod' with ID: 4f8e2c1a-7d9e-4a5b-8c3f-1e6d9a2b5c8e
👑 Assigning role 'developer' to user 'jon_doe@domain.com' in realm 'codemie-prod'...
✅ Role 'developer' successfully assigned to user 'jon_doe@domain.com'
🔗 Creating Identity Provider Link for user 'jon_doe@domain.com'...
✅ Identity Provider Link successfully created for user 'jon_doe@domain.com'
   🔗 Broker User ID: 39b2fa6c-5d9d-491a-a945-ec79fa3c8627
   🔗 Codemie User ID: 4f8e2c1a-7d9e-4a5b-8c3f-1e6d9a2b5c8e
================================================================================
✅ User provisioning for 'Jon Doe' completed successfully!
   📧 Username: jon_doe@domain.com
   🔗 Broker ID: 39b2fa6c-5d9d-491a-a945-ec79fa3c8627
   🔗 Codemie ID: 4f8e2c1a-7d9e-4a5b-8c3f-1e6d9a2b5c8e
   📁 Project: my-project
================================================================================
```

## 📁 File Structure

- `keycloak_user_provisioner.py` - Main script
- `requirements.txt` - Python dependencies
- `README.md` - Documentation

## 🛡️ Security

- Script uses SSL connection (`verify=False` setting for self-signed certificates)
- Authentication tokens are cached for performance improvement
- All error types are handled

## 🚨 Important Notes

1. **Ensure correct configuration** before running in production
2. **Check access permissions** for `codemie_provisioner` account
3. **Script is safe for re-runs** - existing users are not duplicated
