import git
import configparser, hashlib, re, sys


class GitRemoteSubprocess:
    '''A gitremote-helpers remote that uses a shadow directory and launches git-receive-pack and git-upload-pack subprocesses.
    This lets anything that can upload and download a folder be a git remote.
    '''
    def __init__(self, git_dir = '.', url = None, remote_name = None, protocol = None):
        self.orig_url = url
        proto_mkpt = url.find('://')
        if proto_mkpt != -1:
            self.protocol = url[:proto_mkpt]
            url = url[proto_mkpt + len('://'):]
        else:
            self.protocol = protocol
        url = re.sub('/+', '/', url + '/')
        self.fetch_url, self.push_url = self.url2fetchpush(url)
        self.remote_name = remote_name
        self.local = self.path2repo(environ['GIT_DIR'])
        self.shadow_gitdir = os.path.join(self.outer_repo.git_dir, self.__class__.name, self.id())

        try:
            self.remote_shadow = git.Repo(self.shadow_gitdir)
        except:
            self.remote_shadow = None

        if remote_name is not None:
            if self.push_url is not None:
                with self.local_config as cfg:
                    if 'pushurl' not in cfg:
                        cfg['pushurl'] = self.push_url
                        cfg['url'] = self.fetch_url

    @classmethod
    def launch(cls):
        if len(sys.argv) > 3:
            remote_name = sys.argv[2]
            url = sys.argv[3]
        elif len(argv) > 2:
            remote_name = None
            url = sys.argv[2]
        if sys.argv[0].startswith('git-remote-'):
            protocol = sys.argv[0][len('git-remote-'):]
        else:
            protocol = None
        git_dir = os.environ['GIT_DIR']
        remote = cls(git_dir=git_dir, url=url, remote_name=remote_name, protocol=protocol)
        remote.run()

    def run(self):
        ''' process gitremote-helpers commands on stdin'''
        while True:
            line = sys.stdin.readline().rstrip()
            if line == 'capabilities':
                sys.stdout.write('connect\n\n')
            elif line[:8] == 'connect ':
                service = line[8:]
                if service == 'git-upload-pack':
                    self._download()
                elif service == 'git-receive-pack':
                    try:
                        self._download()
                    except:
                        if self.remote_shadow is not None:
                            raise
                    self.remote_shadow = git.Repo.init(shadow_gitdir, mkdir = True, bare = True)

                    # TODO TODO TODO TODO TODO
                    # ==> code went here to copy objects in from other forks (remotes) in a loop with try/catch

                    self.remote_config().set_value('gc', 'auto', 0).release()
                else:
                    raise Exception('Unsupported service: ' + service)

                # TODO TODO TODO TODO TODO
                # ==> spawn the service as a subprocess, in the repo working dir, passing stdin and stdout

                if service == 'git-receive-pack':
                    self.upload()

    def id(self):
        return hashlib.blake2b(self.fetch_url.encode(), digest_size=32).hexdigest()

    def url2fetchpush(self, url):
        '''can override to generate two different urls for push access. both are stored in local config.'''
        return url, None

    @classmethod
    def run(cls, argv):
        '''Launch as a gitremote-helpers remote.'''
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
