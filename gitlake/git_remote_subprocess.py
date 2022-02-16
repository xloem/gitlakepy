import git
import configparser, hashlib, re, sys, os, shutil


class GitRemoteSubprocess:
    '''A gitremote-helpers remote that uses a shadow directory and launches git-receive-pack and git-upload-pack subprocesses.
    This lets anything that can upload and download a folder be a git remote, by implementing the upload() and download() methods.
    '''

    def __init__(self, git_dir = '.', url = None, remote_name = None, protocol = None):
        self.DISTINGUISHING_FILENAME = f'git-remote-{protocol}'
        self.DISTINGUISHING_TEXT = f'This is a {self.DISTINGUISHING_FILENAME} repository.'
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
        self.local = self.path2repo(git_dir)
        self.shadow_gitdir = os.path.join(self.local.git_dir, self.__class__.__name__, self.id())
        self.shadow_gitdir_tmp = os.path.join(self.local.git_dir, self.__class__.__name__, 'git.new')

        try:
            self.remote_shadow = git.Repo(self.shadow_gitdir)
        except:
            self.remote_shadow = None

        if remote_name is not None:
            if self.push_url is not None:
                with self.local_config as cfg:
                    if 'pushurl' not in cfg:
                        cfg['pushurl'] = self.protocol + '://' + self.push_url
                        cfg['url'] = self.protocol + '://' + self.fetch_url

    @classmethod
    def launch(cls, protocol = None):
        '''Launch as a gitremote-helpers remote.'''
        if len(sys.argv) == 3:
            remote_name = sys.argv[1]
            url = sys.argv[2]
        elif len(sys.argv) == 2:
            remote_name = None
            url = sys.argv[1]
        else:
            raise Exception(f'{sys.argv[0]} is a git remote')
        if protocol is None and sys.argv[0].startswith('git-remote-'):
            protocol = sys.argv[0][len('git-remote-'):]
        git_dir = os.environ['GIT_DIR']
        if git_dir is None:
            git_dir = git.Git().rev_parse(git_dir = True)
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

                    self.remote_shadow.git.upload_pack(istream = sys.stdin, output_stream = sys.stdout)

                elif service == 'git-receive-pack':
                    try:
                        self._download()
                    except:
                        if self.remote_shadow is not None:
                            raise
                    self.remote_shadow = git.Repo.init(self.shadow_gitdir, mkdir = True, bare = True)

                    # TODO TODO TODO TODO TODO
                    # ==> code went here to copy objects in from other forks (remotes) in a loop with try/catch
                    # ==> git also has a way to indicate other dirs and urls to pull packfiles from, partial but better than copying
                    ## in git-remote-bsv, this is around line 110, near `if (!fse.existsSync)` and `fse.copyFileSync`

                    self.remote_config().set_value('gc', 'auto', 0).release()

                    self.remote_shadow.git.receive_pack(istream = sys.stdin, output_stream = sys.stdout)

                    self._upload()

                else:
                    raise Exception('Unsupported service: ' + service)
    def id(self):
        return hashlib.blake2b(self.fetch_url.encode(), digest_size=32).hexdigest()

    def download(self, gitdir):
        '''Download or sync to gitdir any available files and paths among:
           config HEAD packed-refs objects/ info/ refs/
        '''
        raise NotImplementedError()

    def upload(self, gitdir):
        '''Upload or sync from gitdir any changed files and paths.
           Loose objects will have been removed.
           The most important paths are:
           HEAD packed-refs objects/ info/ refs/ 
        '''
        raise NotImplementedError()
    
    def _download(self):
        os.makedirs(self.shadow_gitdir, exist_ok=True)
        self.download(self.shadow_gitdir)
        os.makedirs(os.path.join(self.shadow_gitdir, 'refs'), exist_ok=True)
        try:
            self.remote_shadow = git.Repo(self.shadow_gitdir)
            self.remote_config().set_value('gc', 'auto', 0).release()
        except:
            os.rmdir(os.path.join(self.shadow_gitdir, 'refs'))
            raise

    def _upload(self):
        # mirror_path_new is self.shadow_gitdir_tmp
        # mirror_path is self.shadow_gitdir
        if os.path.exists(self.shadow_gitdir_tmp):
            if os.path.isdir(self.shadow_gitdir_tmp) and not os.path.islink(self.shadow_gitdir_tmp):
                shutil.rmtree(self.shadow_gitdir_tmp)
            else:
                os.unlink(self.shadow_gitdir_tmp)
        cleanrepo = git.Repo.clone_from(self.shadow_gitdir, self.shadow_gitdir_tmp, multi_options = ['--mirror', '--bare']) 
        cleanrepo.config_writer().set_value('gc', 'auto', 0).release()
        cleanrepo.git.pack_objects('objects/pack/pack', all=True, include_tag=True, unpacked=True, incremental=True, non_empty=True, local=True, compression=9, delta_base_offset=True, pack_loose_unreachable=True, progress=True)
        cleanrepo.git.prune_packed()

        # each first commit is the head of a commit tree that identifies forks of the same codebase.
        # this tags each first commit for systems that can find files by content, to find forks via small ref files
        first_commits = cleanrepo.git.rev_list('HEAD', max_parents=0).split('\n')
        tag_name = self.fetch_url.replace(':', '/')
        while '//' in tag_name:
            tag_name = tag_name.replace('//', '/')
        for idx, first_commit in enumerate(first_commits):
            cleanrepo.git.tag(tag_name + '/' + first_commit, first_commit)

        cleanrepo.git.update_server_info() # generates files needed for cloning and pulling via http, for systems with dirtree gateways

        with open(os.path.join(self.shadow_gitdir_tmp, self.DISTINGUISHING_FILENAME)) as distinguishing_file:
            distinguishing_file.write(self.DISTINGUISHING_TEXT)

        # code went here to write out a 'description' file, but it seemed important to make the repository description information
        # accessible via git somehow.

        self.upload(self.shadow_gitdir_tmp)

        shutil.rmtree(self.shadow_gitdir)
        os.rename(self.shadow_gitdir_tmp, self.shadow_gitdir)

    def url2fetchpush(self, url):
        '''can override to generate two different urls for push access. both are stored in local config.'''
        return url, None
        
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
    


class ConfigSectionProxy(configparser.SectionProxy):
    def __init__(self, cfgobj, section):
        self._cfg = cfgobj
        super().__init__(self._cfg.config, section)
    def __enter__(self, *params):
        self._cfg.__enter__(*params)
        return self
    def __exit__(self, *params):
        self._cfg.__exit__(*params)

class RemoteConfigProxy(ConfigSectionProxy):
    def __init__(self, remote):
        cfg = remote.config_writer
        super().__init__(cfg, cfg._section_name)
