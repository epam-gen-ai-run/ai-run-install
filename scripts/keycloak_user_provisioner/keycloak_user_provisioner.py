#!/usr/bin/env python3
"""
Keycloak User Provisioner with Token Refresh
Creates users in two Keycloak realms with automatic token refresh
"""

import requests
import json
import sys
import time
import os
from datetime import datetime, timedelta

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

    def authenticate(self):
        """Authentication and obtaining access token"""
        print("🔐 Obtaining new access token...")

        token_url = f"{self.config['keycloak_server_url']}realms/{self.config['master_realm']}/protocol/openid-connect/token"

        data = {
            'client_id': self.config['client_id'],
            'username': self.config['username'],
            'password': self.config['password'],
            'grant_type': 'password'
        }

        try:
            response = self.session.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 300)  # Default 5 minutes

            # Refresh token 30 seconds before expiration
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 30)

            print(f"✅ New access token obtained! Valid until: {self.token_expires_at.strftime('%H:%M:%S')}")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ Authentication error: {e}")
            return False

    def ensure_valid_token(self):
        """Checks and refreshes token when necessary"""
        if not self.access_token or not self.token_expires_at:
            return self.authenticate()

        if datetime.now() >= self.token_expires_at:
            print("⏰ Access token is expiring, refreshing...")
            return self.authenticate()

        return True

    def get_headers(self):
        """Returns headers with current token"""
        if not self.ensure_valid_token():
            raise Exception("Failed to obtain valid access token")

        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def name_to_email(self, full_name):
        """Converts 'First Last' to 'first_last@domain.com'"""
        return full_name.lower().replace(' ', '_').replace('ь', '') + self.email_domain

    def name_to_user_id_format(self, full_name):
        """Converts 'First Last' to 'First_Last@domain.com' for User ID"""
        return full_name.replace(' ', '_') + self.email_domain

    def make_request(self, method, url, **kwargs):
        """Makes HTTP request with automatic token refresh"""
        max_retries = 2

        for attempt in range(max_retries):
            try:
                if 'headers' not in kwargs:
                    kwargs['headers'] = self.get_headers()
                else:
                    kwargs['headers'].update(self.get_headers())

                response = self.session.request(method, url, **kwargs)

                # If we get 401, try to refresh token
                if response.status_code == 401 and attempt < max_retries - 1:
                    print("🔄 Received 401, refreshing token...")
                    if self.authenticate():
                        continue

                return response

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                print(f"⚠️ Request error, attempt {attempt + 1}/{max_retries}: {e}")

        return None

    def find_user_by_email(self, realm, email):
        """Finds user by email"""
        url = f"{self.config['keycloak_server_url']}admin/realms/{realm}/users?email={email}"
        response = self.make_request('GET', url)

        if response and response.status_code == 200:
            users = response.json()
            return users[0] if users else None
        return None

    def create_user(self, realm, email, first_name, last_name):
        """Creates user in specified realm"""
        existing_user = self.find_user_by_email(realm, email)
        if existing_user:
            print(f"ℹ️  User already exists in realm '{realm}'")
            return existing_user['id']

        url = f"{self.config['keycloak_server_url']}admin/realms/{realm}/users"
        user_data = {
            'username': email,
            'email': email,
            'firstName': first_name,
            'lastName': last_name,
            'enabled': True,
            'emailVerified': False
        }

        response = self.make_request('POST', url, json=user_data)

        if response and response.status_code == 201:
            # Get created user ID from Location header
            location = response.headers.get('Location')
            if location:
                user_id = location.split('/')[-1]
                print(f"✅ User created in realm '{realm}' with ID: {user_id}")
                return user_id

        print(f"❌ Error creating user in realm '{realm}': {response.status_code if response else 'No response'}")
        if response:
            print(f"📝 Response: {response.text}")
        return None

    def assign_role_to_user(self, realm, user_id, role_name):
        """Assigns role to user"""
        # Get role
        roles_url = f"{self.config['keycloak_server_url']}admin/realms/{realm}/roles/{role_name}"
        response = self.make_request('GET', roles_url)

        if not response or response.status_code != 200:
            print(f"❌ Role '{role_name}' not found in realm '{realm}'")
            return False

        role_data = response.json()

        # Assign role to user
        assign_url = f"{self.config['keycloak_server_url']}admin/realms/{realm}/users/{user_id}/role-mappings/realm"

        response = self.make_request('POST', assign_url, json=[role_data])

        if response and response.status_code == 204:
            print(f"✅ Role '{role_name}' assigned to user")
            return True

        print(f"❌ Error assigning role: {response.status_code if response else 'No response'}")
        return False

    def update_user_attributes(self, realm, user_id, email, project_name):
        """Updates user attributes"""
        # Get current user data
        user_url = f"{self.config['keycloak_server_url']}admin/realms/{realm}/users/{user_id}"
        response = self.make_request('GET', user_url)

        if not response or response.status_code != 200:
            print(f"❌ Failed to get user data")
            return False

        user_data = response.json()
        current_attributes = user_data.get('attributes', {})

        # Update applications attribute
        applications_values = []

        if 'applications' in current_attributes:
            current_apps = current_attributes['applications']
            if isinstance(current_apps, list):
                for app_string in current_apps:
                    applications_values.extend([app.strip() for app in app_string.split(',')])
            else:
                applications_values = [app.strip() for app in str(current_apps).split(',')]

        # Add email if it's not there
        if email not in applications_values:
            applications_values.append(email)

        # Add project if it's not there
        if project_name not in applications_values:
            applications_values.append(project_name)

        # Update attributes
        user_data['attributes'] = current_attributes
        user_data['attributes']['applications'] = [','.join(applications_values)]

        response = self.make_request('PUT', user_url, json=user_data)

        if response and response.status_code == 204:
            print(f"✅ User attributes updated")
            return True

        print(f"❌ Error updating attributes: {response.status_code if response else 'No response'}")
        return False

    def get_identity_providers(self, realm):
        """Gets list of Identity Providers"""
        url = f"{self.config['keycloak_server_url']}admin/realms/{realm}/identity-provider/instances"
        response = self.make_request('GET', url)

        if response and response.status_code == 200:
            return response.json()

        print(f"❌ Error getting Identity Providers for '{realm}': {response.status_code if response else 'No response'}")
        return []

    def create_identity_provider_link(self, realm, user_id, provider_alias, federated_user_id, federated_username):
        """Creates Identity Provider Link"""
        url = f"{self.config['keycloak_server_url']}admin/realms/{realm}/users/{user_id}/federated-identity/{provider_alias}"

        link_data = {
            "userId": federated_user_id,
            "userName": federated_username
        }

        print(f"🔗 Creating Identity Provider Link in realm '{realm}' with provider '{provider_alias}'...")
        print(f"   URL: {url}")
        print(f"   Data: {json.dumps(link_data, indent=2)}")

        response = self.make_request('POST', url, json=link_data)

        print(f"   Status: {response.status_code if response else 'No response'}")

        if response and response.status_code == 204:
            print(f"✅ Identity Provider Link successfully created in realm '{realm}'!")
            return True
        elif response and response.status_code == 409:
            print(f"ℹ️  Identity Provider Link already exists in realm '{realm}'")
            return True
        else:
            print(f"ℹ️  Identity Provider Link already exists in realm {response.status_code if response else 'No response'}")
            if response:
                print(f"📝 Response: {response.text}")
            return False

    def create_broker_identity_link(self, broker_user_id, username, user_id_format):
        """Creates Identity Provider Link in broker realm"""
        providers = self.get_identity_providers(self.config['broker_realm'])

        # Look for SAML provider
        saml_provider = None
        for provider in providers:
            if provider.get('alias', '').lower() == 'saml':
                saml_provider = provider
                break

        if not saml_provider:
            print(f"⚠️  SAML Identity Provider not found in realm '{self.config['broker_realm']}'")
            return False

        return self.create_identity_provider_link(
            self.config['broker_realm'],
            broker_user_id,
            saml_provider['alias'],
            user_id_format,  # Use format John_Doe@domain.com
            username
        )

    def create_codemie_identity_link(self, codemie_user_id, broker_user_id, username):
        """Creates Identity Provider Link in codemie-prod realm"""
        providers = self.get_identity_providers(self.config['codemie_realm'])

        # Look for broker provider
        broker_provider = None
        for provider in providers:
            if provider.get('alias', '').lower() == 'broker':
                broker_provider = provider
                break

        if not broker_provider:
            print(f"⚠️  Broker Identity Provider not found in realm '{self.config['codemie_realm']}'")
            return False

        return self.create_identity_provider_link(
            self.config['codemie_realm'],
            codemie_user_id,
            broker_provider['alias'],
            broker_user_id,  # Use user ID from broker
            username
        )

    def provision_user(self, full_name, project_name):
        """Creates user in both realms with full configuration"""
        print(f"🚀 Starting user provisioning: '{full_name}' for project '{project_name}'")
        print("=" * 80)

        # Convert name to email and components
        email = self.name_to_email(full_name)
        user_id_format = self.name_to_user_id_format(full_name)
        name_parts = full_name.split()
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

        print(f"📧 Email: {email}")
        print(f"👤 First name: {first_name}")
        print(f"👤 Last name: {last_name}")
        print(f"📁 Project: {project_name}")
        print(f"🌐 Domain: {self.email_domain}")
        print("-" * 80)

        try:
            # Create user in broker
            print(f"🔨 Creating user in realm '{self.config['broker_realm']}'...")
            broker_user_id = self.create_user(
                self.config['broker_realm'],
                email,
                first_name,
                last_name
            )

            if not broker_user_id:
                print(f"❌ Failed to create user in realm '{self.config['broker_realm']}'")
                return False

            # Create user in codemie-prod
            print(f"🔨 Creating user in realm '{self.config['codemie_realm']}'...")
            codemie_user_id = self.create_user(
                self.config['codemie_realm'],
                email,
                first_name,
                last_name
            )

            if not codemie_user_id:
                print(f"❌ Failed to create user in realm '{self.config['codemie_realm']}'")
                return False

            # Assign developer role in codemie-prod
            print(f"🎭 Assigning 'developer' role in realm '{self.config['codemie_realm']}'...")
            self.assign_role_to_user(self.config['codemie_realm'], codemie_user_id, 'developer')

            # Update attributes in codemie-prod
            print(f"📝 Updating user attributes in realm '{self.config['codemie_realm']}'...")
            self.update_user_attributes(self.config['codemie_realm'], codemie_user_id, email, project_name)

            # Create Identity Provider Links
            print("🔗 Creating Identity Provider Links...")

            # Link in broker (User ID in format John_Doe@domain.com)
            self.create_broker_identity_link(broker_user_id, email, user_id_format)

            # Link in codemie-prod (User ID = user ID from broker)
            self.create_codemie_identity_link(codemie_user_id, broker_user_id, email)

            print(f"🎉 User provisioning '{full_name}' completed successfully!")
            print("=" * 80)
            return True

        except Exception as e:
            print(f"💥 Critical error processing user '{full_name}': {e}")
            return False

    def provision_users_batch(self, project_name, user_names):
        """Creates users in batch"""
        if not self.authenticate():
            print("❌ Failed to authenticate")
            return

        print(f"🎯 Starting provisioning of {len(user_names)} users for project '{project_name}'")
        print(f"🌐 Using email domain: {self.email_domain}")
        print("=" * 100)
        print()

        successful_users = []
        failed_users = []

        for i, user_name in enumerate(user_names, 1):
            print(f"📋 Processing user {i}/{len(user_names)}: {user_name}")

            if self.provision_user(user_name, project_name):
                successful_users.append(user_name)
            else:
                failed_users.append(user_name)

            print()

            # Small pause between users to prevent rate limiting
            if i < len(user_names):
                time.sleep(0.5)

        # Final report
        print("=" * 100)
        print("📊 FINAL REPORT")
        print(f"✅ Successfully processed: {len(successful_users)}")
        print(f"❌ Errors: {len(failed_users)}")
        print(f"📊 Total: {len(user_names)}")
        print(f"🌐 Domain used: {self.email_domain}")
        print("=" * 100)

        if failed_users:
            print()
            print("⚠️ USERS WITH ERRORS:")
            for user in failed_users:
                print(f"   ❌ {user}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 keycloak_user_provisioner.py <project_name> <user_names_string> [email_domain]")
        print("Example: python3 keycloak_user_provisioner.py my-project 'John Doe, Jane Smith, Bob Johnson'")
        print("Example with custom domain: python3 keycloak_user_provisioner.py my-project 'John Doe, Jane Smith' @company.com")
        sys.exit(1)

    project_name = sys.argv[1]
    user_names_string = sys.argv[2]

    # Get email domain from command line argument or environment variable or use default
    email_domain = '@domain.com'  # Default domain

    if len(sys.argv) > 3:
        email_domain = sys.argv[3]
    elif 'EMAIL_DOMAIN' in os.environ:
        email_domain = os.environ['EMAIL_DOMAIN']

    # Ensure domain starts with @
    if not email_domain.startswith('@'):
        email_domain = '@' + email_domain

    # Parse user list
    user_names = [name.strip() for name in user_names_string.split(',') if name.strip()]

    if not user_names:
        print("❌ User list is empty")
        sys.exit(1)

    print(f"🎯 Project: {project_name}")
    print(f"👥 Users: {len(user_names)}")
    print(f"🌐 Email domain: {email_domain}")
    print()

    # Create provisioner and run
    provisioner = KeycloakUserProvisioner(email_domain=email_domain)
    provisioner.provision_users_batch(project_name, user_names)

if __name__ == "__main__":
    main()
