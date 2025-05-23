# uluancher-2fauth

A [Uluancher](https://ulauncher.io/) extension to view your two factor accounts in a [2FAuth](https://github.com/Bubka/2FAuth) instance and request an OTP via its API.

## Features

- search your Two-Factor Authentication accounts associated with your 2FAuth account
- select an account and copy the OTP code directly to your clipboard
- this extension does not store any 2FA secrets (they remain on the 2FAuth server) or directly generate the OTP codes (they are requested via the 2FAuth API)

![Screencast](https://github.com/user-attachments/assets/d765f5aa-f80d-4196-8d4a-f057f456132a)


## Setup

This extension requires you to have an account on a [2FAuth](https://github.com/Bubka/2FAuth) instance - a self-hosted web app for managing your Two-Factor Authentication accounts and generating OTP security codes.

In the Ulauncher extension settings, you will need to set two preferences:

- **2FAuth URL:** This is the base URL to your 2FAuth instance (example: https://2fauth.mydomain.com)
- **Personal Access Token:** This is an OAuth token that is used to authenticate the API with your 2FAuth account. To generate one:
1) Login to your 2FAuth account
2) Click the **menu** icon in the footer, next to your account email
3) Go to **Settings**
4) Select the **OAuth** tab
5) Click the **Generate a new token** link
6) Give the token a **name**
7) **Copy** the generate token
8) **Paste** the token into the extension settings

## Usage

To use the extension, enter the keyword (`2fa` by default) into Ulauncher to trigger the extension.

Without a search query, the extension will list your recently used accounts along with the sync and open web app functions.

![image](https://github.com/user-attachments/assets/3e6ed786-1c75-423c-915d-72e09a740942)

Enter the name of the service and/or account to list the matching two factor accounts.

![image](https://github.com/user-attachments/assets/2e546bd3-648c-496a-9aa2-30dd4df6d3f6)

When an account is selected, you can view the OTP code and choose to copy it directly to your clipboard or open the account editor on the 2FAuth website.

![image](https://github.com/user-attachments/assets/7fd2fec2-4ec4-4d06-bd4a-fe095128f31a)

## Account Cache

To enable quick account lookups, the basic information about your two factor accounts (service name, account name, and 2FAuth account id number) are cached locally (in memory) and the two factor account icons are saved to disk.  The local cache will be updated automatically periodically (after 24 hours, by default).  However, the cache can be updated manually by selecting the 'Sync Accounts' item.
