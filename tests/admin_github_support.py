"""In-memory gh process adapter. No credentials, sockets, or external writes."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit,parse_qs

from southpaw_tools.admin_github import PREFIX


class FakeGh:
    def __init__(self):
        self.releases={};self.asset_bytes={};self.latest=None;self.calls=[]
        self.fail=None;self.corrupt_download=False

    def __call__(self,args,body):
        index=args.index('--method');method=args[index+1];endpoint=args[index+2]
        self.calls.append((method,endpoint))
        if self.fail and self.fail(method,endpoint):
            return subprocess.CompletedProcess(args,7,b'HTTP/2.0 500 Error\r\n\r\n{}',b'')
        def reply(data,status=200):
            raw=data if isinstance(data,bytes) else json.dumps(deepcopy(data)).encode()
            return subprocess.CompletedProcess(args,0,f'HTTP/2.0 {status} OK\r\n\r\n'.encode()+raw,b'')
        path=endpoint.split('?')[0]
        if method=='GET' and path=='user':return reply({'login':'toast-source'})
        if method=='GET' and path==PREFIX+'/releases':return reply(list(self.releases.values()))
        if method=='GET' and path==PREFIX+'/releases/latest':return reply(self.releases[self.latest])
        if method=='POST' and path==PREFIX+'/releases':
            values=json.loads(body);identity=len(self.releases)+1
            record={'id':identity,'assets':[],**values};self.releases[identity]=record
            return reply(record,201)
        if path.startswith(PREFIX+'/releases/assets/'):
            raw=self.asset_bytes[int(path.rsplit('/',1)[1])]
            if self.corrupt_download:raw=bytes([raw[0]^1])+raw[1:]
            return reply(raw)
        if method=='POST' and endpoint.startswith('https://uploads.github.com/'):
            parsed=urlsplit(endpoint);name=parse_qs(parsed.query)['name'][0]
            identity=int(parsed.path.split('/')[-2]);record=self.releases[identity]
            if any(a['name']==name for a in record['assets']):
                return subprocess.CompletedProcess(args,1,b'HTTP/2.0 422 Error\r\n\r\n{}',b'')
            raw=Path(args[args.index('--input')+1]).read_bytes()
            asset_id=len(self.asset_bytes)+100
            asset={'id':asset_id,'name':name,'size':len(raw),'digest':'sha256:'+hashlib.sha256(raw).hexdigest(),'state':'uploaded'}
            record['assets'].append(asset);self.asset_bytes[asset_id]=raw
            return reply(asset,201)
        if path.startswith(PREFIX+'/releases/'):
            identity=int(path.rsplit('/',1)[1]);record=self.releases[identity]
            if method=='PATCH':
                record.update(json.loads(body));self.latest=identity
            return reply(record)
        raise AssertionError('Unexpected mock gh operation: '+method+' '+path)
