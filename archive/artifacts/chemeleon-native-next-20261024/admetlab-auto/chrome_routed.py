#!/usr/bin/env python3
"""Existing user Chrome session, 500-row web batches, verified per-host Wi-Fi route."""
import argparse, socket, subprocess, time, re, sys
from pathlib import Path
from collect import Collector, StopRun, save, now
from current_chrome import CurrentChrome, process
ROOT=Path(__file__).resolve().parent

def check_route():
    ips=sorted({x[4][0] for x in socket.getaddrinfo('admetlab3.scbdd.com',443,type=socket.SOCK_STREAM)})
    if not ips:raise StopRun('ADMETlab DNS returned no addresses.')
    evidence={}
    for ip in ips:
        r=subprocess.run(['/sbin/route','-n','get',ip],capture_output=True,text=True,check=True).stdout
        match=re.search(r'interface:\s*(\S+)',r)
        if not match or match.group(1)!='en0':raise StopRun('ADMETlab route is not Wi-Fi/en0: '+ip+'; configure the host route first.')
        evidence[ip]=r
    default=subprocess.run(['/sbin/route','-n','get','default'],capture_output=True,text=True,check=True).stdout
    if not re.search(r'interface:\s*utun\d+',default):raise StopRun('Default route is no longer the VPN. Stopped before submission.')
    return {'utc':now(),'destination_routes':evidence,'default_route':default}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--max-batches',type=int,default=11)
    p.add_argument('--status',action='store_true')
    p.add_argument('--output',type=Path,default=Path.home()/'Downloads/ADMETlab-Chrome-direct-500')
    a=p.parse_args()
    if a.max_batches<1:p.error('max-batches must be positive')
    c=Collector(ROOT/'../../cyp-admet500-pilot-20261025/next-official-5155.csv',a.output,500)
    try:
        c.emit('status',**c.status())
        if a.status:return 0
        pending=[i for i in range(len(c.batches)) if not c.completed(i)][:a.max_batches]
        if not pending:return 0
        save(c.root/'route-check.json',check_route())
        chrome=CurrentChrome(c.base)
        save(c.root/'chrome-session.json',{'window_id':chrome.window_id,'tab_id':chrome.tab_id,'utc':now()})
        for n,i in enumerate(pending):
            save(c.folder(i)/'route-check.json',check_route())
            process(c,chrome,i,900,False)
            c.merge()
            if n+1<len(pending):time.sleep(20)
        c.emit('finished',**c.status());return 0
    except (Exception,KeyboardInterrupt) as e:
        c.emit('stopped',error=str(e),**c.status());return 2
    finally:c.close()
if __name__=='__main__':sys.exit(main())
