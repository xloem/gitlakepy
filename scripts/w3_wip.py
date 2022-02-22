
'''more effective to make boilerplate for git-annex chunking than to make this library file
   can use npm @web3.storage/w3 subprocess'''

MAX_PUT_RETRIES = 5
DEFAULT_API = 'https://api.web3.storage'

class Client:
    def __Init__(token, endpoint = DEFAULT_API):
        self.token = token
        self.endpoint = API
    @property
    def headers(self):
        return {
            'Authorization': 'Bearer ' + self.token,
            'X-Client': 'gitlakepy',
        }
    def put(self, files : list, onRootCidReady = None, onStoredChunk = None, maxRetries = MAX_PUT_RETRIES, wrapWithDirectory = True, name = None):
