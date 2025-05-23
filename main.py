from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent, PreferencesEvent, PreferencesUpdateEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.ActionList import ActionList
import logging
import requests
import time
import os
from collections import deque

logger = logging.getLogger(__name__)


class AuthExtension(Extension):

    def __init__(self):
        super().__init__()

        # extension properties
        self.url = ""
        self.pat = ""
        self.keyword = ""
        self.expiry = 24
        self.cache = {
            "updated": 0,
            "accounts": []
        }
        self.recent_max = 5
        self.recent = deque([], maxlen=self.recent_max)

        # set path to cached account icons
        file_path = os.path.abspath(__file__)
        self.icon_dir_path = f"{os.path.dirname(file_path)}/account_icons"

        # event listeners
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


    #
    # UPDATE CACHE
    # - Fetch the account metadata via the 2FAuth API
    # - Download and cache the account icons
    #
    def update_cache(self):
        logger.debug('Updating 2FAuth Cache...')

        # Error message encountered while updating the cache
        error = None

        # Check for required extension properties
        if self.url == "":
            error = "2FAuth URL not set"
        if self.pat == "":
            error = "2FAUTH PAT not set"

        # Update the account cache
        if error is None:
            logger.debug(f"Fetching 2FAuth accounts from {self.url}...")
            try:
                url = f"{self.url}/api/v1/twofaccounts"
                headers = {
                    "Authorization": f"Bearer {self.pat}"
                }
                response = requests.get(url, headers=headers)
                data = response.json()
                if "message" in data:
                    error = f"API Error = {data['message']}"
                else:
                    logger.debug(f"Fetched {len(data)} 2FAuth accounts")
                    self.cache["updated"] = time.time()
                    self.cache["accounts"] = data
            except Exception as err:
                error = f"Network Error = {err}"

        # Update the account icons
        if error is None:
            logger.debug(f"Fetching 2FAuth account icons from {self.url} to {self.icon_dir_path}...")

            for account in self.cache["accounts"]:
                icon = account["icon"]
                icon_file_path = f"{self.icon_dir_path}/{icon}"

                if not os.path.isfile(icon_file_path):
                    logger.debug(f"Fetching 2FAuth icon for account #{account['id']}...")
                    url = f"{self.url}/storage/icons/{icon}"
                    response = requests.get(url)
                    with open(icon_file_path, "wb") as f:
                        f.write(response.content)

        # Log the error message, if set
        if error is not None:
            logger.error(f"Error Updating 2FAuth Cache: {error}")

        return(error)

    #
    # QUERY ACCOUNTS
    # - Find 2fa accounts that match the query
    #
    def query_accounts(self, query):
        logger.debug(f"Query 2FAuth Accounts {query}")

        # empty query, return no accounts
        if ( query == "" ):
            return([])

        # filter accounts by query
        accounts = self.cache["accounts"]
        tokens = query.split()
        for token in tokens:
            matches = list(filter(lambda account: token.lower() in account["account"].lower() or token.lower() in account["service"].lower(), accounts))
            accounts = matches
        return(accounts)

    #
    # GET OTP
    # - Fetch the current OTP for the specified account
    #
    def get_otp(self, account_id):
        logger.debug(f"Fetching 2FAuth OTP for Account #{account_id} from {self.url}...")
        otp = ""

        try:
            url = f"{self.url}/api/v1/twofaccounts/{account_id}/otp"
            headers = {
                "Authorization": f"Bearer {self.pat}"
            }
            response = requests.get(url, headers=headers)
            data = response.json()
            otp = data["password"]
            return(otp)

        except Exception as err:
            logger.error(f"2FAuth Error while fetching OTP: {err}")
            return(err)


#
# PREFERENCES EVENT LISTENER
# - triggered on start
# - set the extension preferences
# - update the cache
#
class PreferencesEventListener(EventListener):
    def on_event(self, event, extension):
        extension.url = event.preferences["2fauth_url"]
        extension.pat = event.preferences["2fauth_pat"]
        extension.keyword = event.preferences["2fauth_kw"]
        extension.expiry = float(event.preferences["2fauth_expiry"])
        extension.recent_max = int(event.preferences["2fauth_recent_max"])
        extension.recent = deque([], maxlen=extension.recent_max)
        extension.update_cache()


#
# PREFERENCES UPDATE EVENT LISTENER
# - triggered when extension settings are updated
# - update the extension preferences
# - update the cache (for updated url and pat)
#
class PreferencesUpdateEventListener(EventListener):
    def on_event(self, event, extension):
        if event.id == "2fauth_url":
            extension.url = event.new_value
            extension.update_cache()
        elif event.id == "2fauth_pat":
            extension.pat = event.new_value
            extension.update_cache()
        elif event.id == "2fauth_kw":
            extension.keyword = event.new_value
        elif event.id == "2fauth_expiry":
            extension.expiry = float(event.new_value)
        elif event.id == "2fauth_recent_max":
            extension.recent_max = int(event.new_value)
            extension.recent = deque([], maxlen=extension.recent_max)


#
# KEYWORD QUERY EVENT LISTENER
# - triggered on keyword activation
# - check for required extension preferences
# - update the cache, if it has expired
# - find accounts that match the user query
# - display all matching accounts
#
class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        query = event.get_argument() or ""
        items = []

        logger.debug(f"2FAuth Query: {query}")

        # Display error if required settings are not set
        if extension.url == "":
            items.append(ExtensionResultItem(
                icon='images/warning.png',
                name='Configuration Error',
                description='2FAuth URL not set - add this in extension settings',
                on_enter=HideWindowAction()
            ))
        elif extension.pat == "":
            items.append(ExtensionResultItem(
                icon='images/warning.png',
                name='Configuration Error',
                description='2FAuth PAT not set - add this in extension settings',
                on_enter=HideWindowAction()
            ))

        # Process user request
        else:

            # check if the cache has expired
            now = time.time()
            expiry = extension.cache["updated"] + (extension.expiry*3600)
            if now > expiry:
                logger.debug("2FAuth Cache has expired")
                error = extension.update_cache()

                # error encountered while refreshing the cache
                if error is not None:
                    items.append(ExtensionResultItem(
                        icon='images/warning.png',
                        name='Could not sync accounts',
                        description=error,
                        on_enter=HideWindowAction()
                    ))

            # find matching accounts
            accounts = extension.query_accounts(query)

            # display matching accounts
            for account in accounts:
                icon_file_path = f"{extension.icon_dir_path}/{account['icon']}"
                if not os.path.isfile(icon_file_path):
                    icon_file_path = "images/account.png"
                items.append(ExtensionResultItem(
                    icon=icon_file_path,
                    name=account["service"],
                    description=account["account"],
                    on_enter=ExtensionCustomAction({ "action": "fetch", "account": account }, keep_app_open=True)
                ))

            # Display recent accounts and extension functions if no matching accounts
            if len(accounts) == 0:

                # add query instructions
                items.append(ExtensionResultItem(
                    icon='images/icon.png',
                    name='Account Search',
                    description='Enter the service and/or account name',
                    on_enter=DoNothingAction()
                ))

                # add recent accounts
                for account in extension.recent:
                    icon_file_path = f"{extension.icon_dir_path}/{account['icon']}"
                    if not os.path.isfile(icon_file_path):
                        icon_file_path = "images/account.png"
                    items.append(ExtensionResultItem(
                        icon=icon_file_path,
                        name=account["service"],
                        description=account["account"],
                        on_enter=ExtensionCustomAction({ "action": "fetch", "account": account }, keep_app_open=True)
                    ))

                # add sync function
                items.append(ExtensionResultItem(
                    icon='images/sync.png',
                    name='Sync Accounts',
                    description='Refresh list of cached accounts',
                    on_enter=ExtensionCustomAction({ "action": "update" }, keep_app_open=True)
                ))

                # add open website function
                items.append(ExtensionResultItem(
                    icon='images/launch.png',
                    name='Open Website',
                    description='Open 2FAuth website in browser',
                    on_enter=OpenUrlAction(extension.url)
                ))

        return RenderResultListAction(items)


#
# CUSTOM EVENT LISTENER
# - action = update: refresh the cache
# - action = fetch: request an OTP from the 2FAuth API
#
class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        action = data["action"]

        # UPDATE CACHE
        if action == "update":
            logger.debug("2FAuth Action: refresh the cache")

            # update the cache
            error = extension.update_cache()

            # error encountered while refreshing the cache
            if error is not None:
                return RenderResultListAction([
                    ExtensionResultItem(
                        icon='images/warning.png',
                        name='Could not sync accounts',
                        description=error,
                        on_enter=HideWindowAction()
                    )
                ])

            # sync successful
            else:
                return RenderResultListAction([
                    ExtensionResultItem(
                        icon='images/sync.png',
                        name='All Done!',
                        on_enter=ActionList([
                            SetUserQueryAction(f"{extension.keyword}"),
                            SetUserQueryAction(f"{extension.keyword} ")
                        ])
                    )
                ])

        # FETCH OTP
        elif action == "fetch":
            account = data["account"]
            logger.info(f"2FAuth Action: fetch OTP for account #{account['id']}")

            # fetch the OTP
            otp = extension.get_otp(account["id"])

            # set edit account url
            edit_url = f"{extension.url}/account/{account['id']}/edit"

            # add account to recent list
            extension.recent.appendleft(account)

            return RenderResultListAction([
                ExtensionResultItem(
                    icon="images/account.png",
                    name=otp,
                    description="Copy to clipboard",
                    on_enter=CopyToClipboardAction(otp)
                ),
                ExtensionResultItem(
                    icon="images/edit.png",
                    name="Edit Account",
                    description="Open account editor in browser",
                    on_enter=OpenUrlAction(edit_url)
                )
            ])


if __name__ == '__main__':
    AuthExtension().run()