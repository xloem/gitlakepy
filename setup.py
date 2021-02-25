#!/usr/bin/env python3
from distutils.core import setup

setup(name='gitlake',
      version='0.37',
      description='Decentralized special remotes for git-annex',
      author='Karl Semich',
      author_email='0xloem@gmail.com',
      url='https://github.com/xloem/gitlakepy',
      py_modules=['gitlake'],
      scripts=['scripts/git-annex-remote-freenet','scripts/git-annex-remote-siaskynet','scripts/git-annex-remote-bsv'],
      install_requires=['fcp', 'siaskynet', 'polyglot-bitcoin', 'annexremote', 'flock', 'bitcoinx'],
     )
