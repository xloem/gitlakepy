#!/usr/bin/env python2

from distutils.core import setup

setup(name='gitlakepy',
      version='0.5',
      description='Decentralized special remotes for git-annex',
      author='Karl Semich',
      author_email='gmkarl@gmail.com',
      url='https://github.com/gmkarl/gitlakepy',
      scripts=['scripts/git-annex-remote-freenet'],
      requires=['fcp'],
     )
