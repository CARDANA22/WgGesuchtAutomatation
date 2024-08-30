import requests
import json

class WgGesuchtClient:

    # Constants
    API_URL = 'https://www.wg-gesucht.de/api/{}'
    APP_VERSION = '1.28.0'
    APP_PACKAGE = 'com.wggesucht.android'
    CLIENT_ID = 'wg_mobile_app'
    USER_AGENT = 'Mozilla/5.0 (Linux; Android 6.0; Google Build/MRA58K; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.186 Mobile Safari/537.36'

    # Constructor
    def __init__(self):
        self.userId, self.accessToken, self.refreshToken, self.phpSession, self.devRefNo = None, None, None, None, None

    # Performs a call to api
    def request(self, method: str, endpoint: str, params: object = None, payload: object = None, attempt: int = 0):

        # Build url
        url = self.API_URL.format(endpoint)

        # Build cookies
        cookies = [
            'PHPSESSID={}'.format(self.phpSession) if self.phpSession else None,
            'X-Client-Id={}'.format(self.CLIENT_ID),
            'X-Refresh-Token={}'.format(self.refreshToken) if self.refreshToken else None,
            'X-Access-Token={}'.format(self.accessToken) if self.accessToken else None,
            'X-Dev-Ref-No={}'.format(self.devRefNo) if self.devRefNo else None,
        ]
        cookieHeader = '; '.join(cookie for cookie in cookies if cookie)

        # Build headers
        headers = {
            'X-App-Version': self.APP_VERSION,
            'User-Agent': self.USER_AGENT,
            'Content-Type': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': 'application/json',
            'X-Client-Id': self.CLIENT_ID,
            'X-Authorization': 'Bearer {}'.format(self.accessToken) if self.accessToken else None,
            'X-User-Id': self.userId if self.userId else None,
            'X-Dev-Ref-No': self.devRefNo if self.devRefNo else None,
            'Cookie': cookieHeader,
            'X-Requested-With': self.APP_PACKAGE,
            'Origin': 'file://' if not self.accessToken else None
        }

        # Perform request
        try:
            r = requests.request(method=method, url=url, headers=headers, params=params, data=payload)
            r.raise_for_status()  # Dies wird einen Fehler auslösen, wenn der Status-Code nicht im 200er Bereich liegt
            return r  # Erfolgreiche Antwort
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            print(f"Response content: {e.response.text if e.response else 'No response content'}")
            return None

    # Import account data
    def importAccount(self, config: object):
        self.userId = config['userId']
        self.accessToken = config['accessToken']
        self.refreshToken = config['refreshToken']
        self.phpSession = config['phpSession']
        self.devRefNo = config['devRefNo']

    # Export account data
    def exportAccount(self):
        return {
            'userId': self.userId,
            'accessToken': self.accessToken,
            'refreshToken': self.refreshToken,
            'phpSession': self.phpSession,
            'devRefNo': self.devRefNo
        }

    # Login
    def login(self, username: str, password: str):
        # Build payload
        payload = {
            'login_email_username': username,
            'login_password': password,
            'client_id': self.CLIENT_ID,
            'display_language': 'de'
        }

        # Request api
        r = self.request('POST', 'sessions', None, json.dumps(payload))

        # Check for response success
        if r is not None:
            # Success, set data
            jsonBody = r.json()
            print("Login response:", json.dumps(jsonBody, indent=2))
            self.accessToken = jsonBody['detail']['access_token']
            self.refreshToken = jsonBody['detail']['refresh_token']
            self.userId = jsonBody['detail']['user_id']
            self.devRefNo = jsonBody['detail']['dev_ref_no']
            self.phpSession = r.cookies.get('PHPSESSID', '')
            return True
        else:
            # Failure
            print("Login failed")
            return False

    # Refresh login token
    def refreshToken(self):

        # Build payload
        payload = {
            'grant_type': 'refresh_token',
            'access_token': self.accessToken,
            'refresh_token': self.refreshToken,
            'client_id': self.CLIENT_ID,
            'dev_ref_no': self.devRefNo,
            'display_language': 'de'
        }

        # Build url
        url = 'sessions/users/{}'.format(self.userId)

        # Request api
        r = self.request('POST', url, None, json.dumps(payload))

        # Check for response success
        if r:

            # Success, set new data
            jsonBody = r.json()
            self.accessToken = jsonBody['detail']['access_token']
            self.refreshToken = jsonBody['detail']['refresh_token']
            self.devRefNo = jsonBody['detail']['dev_ref_no']
            return True

        else:

            # Failture
            return False

    # My Profile
    def myProfile(self):
        
        # Build url
        url = 'public/users/{}'.format(self.userId)

        # Request api
        r = self.request('GET', url)

        # Check for response success
        if r:

            # Success
            return r.json()

        else:

            # Failture
            return False

    # Search city by name
    def findCity(self, query: str):
        url = 'location/cities/names/{}'.format(query)
        r = self.request('GET', url)
        if r:
            response_json = r.json()
            print("City search response:", json.dumps(response_json, indent=2))
            if '_embedded' in response_json and 'cities' in response_json['_embedded']:
                return response_json['_embedded']['cities']
            else:
                print("Unexpected response structure for city search")
                return []
        else:
            print("City search request failed")
            return []

    # Offers list
    def offers(self, cityId: str, categories: str, maxRent: str, minSize: str, max_wg_size: int, page: str = '1'):
        url = 'asset/offers/'
        params = {
            'ad_type': '0',
            'categories': categories,
            'city_id': cityId,
            'noDeact': '1',
            'img': '1',
            'limit': '20',
            'rMax': maxRent,
            'sMin': minSize,
            'rent_types': categories,
            'page': page
        }
        r = self.request('GET', url, params)
        if r:
            response_json = r.json()
            if '_embedded' in response_json and 'offers' in response_json['_embedded']:
                offers = response_json['_embedded']['offers']
                filtered_offers = [offer for offer in offers if int(offer.get('flatshare_inhabitants_total', 0)) <= max_wg_size]
                return filtered_offers
            else:
                print("Unexpected response structure for offers")
                return []
        else:
            print("Offers request failed")
            return []

    # Offer detail
    def offerDetail(self, offerId: str):

        # Build url
        url = 'public/offers/{}'.format(offerId)

        # Request api
        r = self.request('GET', url)

        # Check for response success
        if r:

            # Success
            return r.json()

        else:

            # Failture
            return False

    # Contact offer
    def contactOffer(self, offerId: str, message: str):
        
        # Build payload
        payload = {
            'user_id': self.userId,
            'ad_type': 0,
            'ad_id': int(offerId),
            'messages':[
                {
                    'content': message,
                    'message_type': 'text'
                }
            ]
        }

        # Request api
        r = self.request('POST', 'conversations', None, json.dumps(payload))

        # Check for response success
        if r:

            # Success, return all conversation messanges
            return r.json()['messages']

        else:

            # Failture
            return False

    # Conversations list
    def conversations(self, page: str = '1'):

        # Build url
        url = 'conversations/user/{}'.format(self.userId)

        # Build params
        params = {
            'page': page,
            'limit': '25',
            'language': 'de',
            'filter_type': '0'
        }

        # Request api
        r = self.request('GET', url, params)

        # Check for response success
        if r:

            # Success, just return conversation threads
            return r.json()['_embedded']['conversations']

        else:

            # Failture
            return False

    # Conversations detail
    def conversationDetail(self, conversationId: str):

        # Build url
        url = 'conversations/{}/user/{}'.format(conversationId, self.userId)

        # Build params
        params = {
            'language': 'de'
        }

        # Request api
        r = self.request('GET', url, params)

        # Check for response success
        if r:

            # Success
            return r.json()

        else:

            # Failture
            return False