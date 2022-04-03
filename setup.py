#!/usr/bin/env python3
from distutils.core import setup

setup(name='gitlake',
      version='0.44',
      description='Decentralized special remotes for git-annex',
      author='Karl Semich',
      author_email='0xloem@gmail.com',
      url='https://github.com/xloem/gitlakepy',
      packages=['gitlake'],
      scripts=[
          'scripts/git-annex-remote-freenet',
          'scripts/git-annex-remote-siaskynet',
          'scripts/git-annex-remote-bsv',
          'scripts/git-annex-remote-arkb-subprocess',
          'scripts/git-remote-arkb-subprocess',
          'scripts/git-annex-remote-w3-subprocess',
#          'scripts/git-annex-remote-w3-hybrid'
      ],
      install_requires=['siaskynet', 'polyglot-bitcoin', 'annexremote', 'flock', 'bitcoinx'],
)
