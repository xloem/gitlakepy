import git
import configparser, hashlib, re, sys


class GitRemoteSubprocess:
    '''A git-remotehelpers remote that uses a shadow directory and launches git-receive-pack and git-upload-pack subprocesses.'''
    def __init__(self, argv = [], protocols = ['http://', 'https://'], remote_name = None, url = None, pushurl = None):
        if len(argv) > 3:
            remote_name = argv[2]
            url = argv[3]
        elif len(argv) > 2:
            url = argv[2]
        self.orig_url = url
        for protocol in protocols:
            url = url.replace(protocol, '')
        url = re.sub('/+', '/', url + '/')
        self.fetch_url, self.push_url = self.url2fetchpush(url)
        self.remote_name = remote_name
        self.local = repo
        shadow_gitdir = os.path.join(self.outer_repo.git_dir, 'gitlake', self.id())
        self.remote_shadow = git.Repo.init(shadow_gitdir, mkdir = True)

        if remote_name is not None:
            if self.push_url is not None:
                with self.local_config as cfg:
                    if 'pushurl' not in cfg:
                        cfg['pushurl'] = self.push_url
                        cfg['url'] = self.fetch_url

    def run(self):
        ''' process git-remotehelpers commands on stdin'''
        while True:
            line = sys.stdin.readline().rstrip()
            if line == 'capabilities':
                sys.stdout.write('connect\n\n')
            elif line == 'connect git-upload-pack':
                # fetch
            elif line == 'connect git-receive-pack':
                # push

    def id(self):
        return hashlib.blake2b(self.fetch_url.encode(), digest_size=32).hexdigest()

    def url2fetchpush(self, url):
        '''can override to generate two different urls for push access. both are stored in local config.'''
        return url, None

    @classmethod
    def run(cls, argv):
        '''Launch as a git-remotehelpers remote.'''
        if len(argv) > 3:
            remotename = argv[2]
            origurl = argv[3]
        else:
            remotename = None
            origurl = argv[2]

        remotename = argvp3[ 
        
    @property
    def local_config(self):
        return RemoteConfigProxy(self.remote)

    @property
    def remote(self):
        return self.local.remote(self.remote_name)

    @property
    def remote_config(self):
        return self.remote_shadow.config_writer()

    @staticmethod
    def path2repo(path):
        return git.Repo(path, search_parent_directories = True)
    


class ConfigSectionProxy(configparser.ConfigSectionProxy):
    def __init__(self, cfgobj, section)
        self._cfg = cfgobj
        super().__init__(self._cfg, section)
    def __enter__(self, *params):
        self._cfg.__enter__(*params)
        super().__enter__(*params)
        return self
    def __exit__(self, *params):
        super().__exit__(*params)
        self._cfg.__exit__(*params)

class RemoteConfigProxy(ConfigSectionProxy):
    def __init__(self, remote)
        cfg = remote.config_writer()
        super.__init__(cfg, cfg._section_name)
