#!/usr/bin/env python3
import asyncio
import pathlib
import signal
import stat
import sys

try:
    import aiohttp
    import aiofiles
    import dulwich.repo
    import tqdm.asyncio
except:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'aiohttp', 'aiofiles', 'dulwich', 'tqdm'])
    import aiohttp
    import aiofiles
    import dulwich.repo
    import tqdm.asyncio

class amain:
    def __init__(self, repo_path, gateway = 'https://arweave.net/', files_at_once = 3, chunks_at_once = 32):
        self.repo = dulwich.repo.Repo(repo_path)
        self.gateway = gateway
        self.files_at_once = asyncio.Semaphore(files_at_once)
        self.chunks_at_once = asyncio.Semaphore(chunks_at_once)

    async def _bounded(self, sem, coro):
        async with sem:
            return await coro

    async def _fetch_chunk(self, ditemid, progress):
        subchunks = []
        async with self.http.get(self.gateway + ditemid) as response:
            async for subchunk in response.content.iter_any():
                subchunks.append(subchunk)
                progress.update(len(subchunk))
        return subchunks

    async def _fetch_file(self, logblob, name, path, size):
        path.parent.mkdir(exist_ok=True,parents=True)
        async with aiofiles.open(str(path), 'wb') as ofh:
          with tqdm.tqdm(desc=name, total=size, unit='B', unit_scale=True, unit_divisor=1024) as progress:
            for line in logblob.splitlines():
                for pfx in (b'https://', b'arkb-subprocess://'):
                    idx = line.find(pfx)
                    if idx >= 0:
                        url = line[idx:].strip().decode()
                        break
                else:
                    continue
                if pfx == b'arkb-subprocess://':
                    ditemid = url[len(pfx):]
                    loop = asyncio.get_event_loop()
                    chunks = [
                        loop.create_task(self._bounded(self.chunks_at_once, self._fetch_chunk(subditemid.decode().strip(), progress)))
                        async for subfolder in (await self.http.get(self.gateway + ditemid)).content
                        async for subditemid in (await self.http.get(self.gateway + ditemid + '/' + subfolder.decode().strip())).content
                    ]
                    #self.queued_tasks.append(chunks)
                    for chunk in chunks:
                        subchunks = await chunk
                        for subchunk in subchunks:
                            await ofh.write(subchunk)
                else:
                    response = await self.http.get(url)
                    async for chunk in response.content.iter_any():
                        await ofh.write(chunk)
                        progress.update(len(chunk))

    async def __call__(self):
        key_name_path_sizes = {}
        key_logs = {}
        refs = self.repo.refs.as_dict()
        head = self.repo[self.repo.head()]
        for name, mode, sha in dulwich.object_store.iter_tree_contents(self.repo, head.tree):
            if stat.S_ISLNK(mode):
                location = self.repo[sha].data.decode()
                location = (pathlib.Path(self.repo.path) / name.decode()).parent / location
                location = location.resolve()
                key = location.name
                size = int(key.split('--',1)[0].split('-s')[-1])
                if not location.exists() or location.stat().st_size != size:
                    key_name_path_sizes[key] = name.decode(), location, size
        gitannex = [val for ref, val in refs.items() if ref.endswith(b'git-annex')][0]
        gitannex = self.repo[gitannex]
        for name, mode, sha in dulwich.object_store.iter_tree_contents(self.repo, gitannex.tree):
            if name.endswith(b'.log.web'):
                key = name[name.rfind(b'/')+1:-len(b'.log.web')].decode()
                if key in key_name_path_sizes:
                    key_logs[key] = self.repo[sha]
        async with aiohttp.ClientSession() as http:
            self.http = http
            return await asyncio.gather(*[
                self._bounded(self.files_at_once, self._fetch_file(key_logs[key], *key_name_path_sizes[key]))
                for key in key_logs
            ])

if __name__ == '__main__':
    # This restores the default Ctrl+C signal handler, which just kills the process
    #signal.signal(signal.SIGINT, signal.SIG_DFL)

    try:
        asyncio.run(amain('.')())
    except:
        import os
        import logging
        logging.getLogger(__name__).exception('exception')
        os._exit(1)
