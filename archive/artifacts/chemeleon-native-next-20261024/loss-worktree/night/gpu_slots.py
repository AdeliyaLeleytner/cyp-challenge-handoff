"""Host-local exclusive GPU leases shared by this campaign's ORX queues."""
from pathlib import Path
import fcntl
ROOT=Path('/workspace/cyp-repro/gpu-slots')
def acquire(gpu):
 ROOT.mkdir(parents=True,exist_ok=True)
 handle=(ROOT/f'gpu-{gpu}.lock').open('a+')
 try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:handle.close();return None
 return handle
def release(handle):
 fcntl.flock(handle,fcntl.LOCK_UN);handle.close()
