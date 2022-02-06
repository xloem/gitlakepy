import git


class GitRemoteSubprocess:
    '''A remote that uses a shadow directory and launches git-receive-pack and git-upload-pack subprocesses.'''
    def __init__(self, repo, remote_name):#tree_dir, name, **repo_kwparams):
        #self.outer_repo = git.Repo(tree_dir, **repo_kwparams)
        self.outer_repo = repo
        self.inner_gitdir = os.path.join(self.outer_repo.git_dir, 'gitlake', remote_name)
        self.inner_repo = git.Repo.init(self.inner_gitdir, mkdir = True)

    @staticmethod
    def path2repo(path):
        return git.Repo(path, search_parent_directories = True)
    
