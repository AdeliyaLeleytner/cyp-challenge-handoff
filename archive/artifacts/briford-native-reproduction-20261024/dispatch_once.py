"""One authorized delayed submission of an already reviewed immutable CSV, then read-only result checks."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,os,sys,time
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'package/dispatch_runtime'))
from night.submit_candidate import send_prepared,_json_bytes
from check_native_leaderboard import check

def state(status,**kw):
 value={'status':status,'updated_utc':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),**kw};tmp=P/'dispatch-status.tmp';tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(P/'dispatch-status.json');print(json.dumps(value),flush=True)
def main():
 lock=(P/'package/dispatch.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 review=json.loads((P/'package/dispatch-review.json').read_text());assert review['root_review_complete'] is True
 rt=P/'package/dispatch_runtime/night/submit_candidate.py';assert hashlib.sha256(rt.read_bytes()).hexdigest()==review['runtime_sha256']
 directory=Path(review['intent_dir']);body=json.loads((directory/'intent.json').read_text());identity=hashlib.sha256(_json_bytes(body)).hexdigest();assert identity==review['intent_id']==directory.name
 csv_sha=hashlib.sha256((directory/'submission.csv').read_bytes()).hexdigest();assert csv_sha==review['csv_sha256']==body['submission_csv']['sha256']
 assert body['validation']['official_validator_passed'] and body['validation']['independent_id_smiles_check_passed'] and not body['rho_above_one']
 prepared={'intent_id':identity,'intent_dir':str(directory),'csv_sha256':csv_sha,'intent':body}
 deadline=datetime.fromisoformat(review['not_before_utc']);state('queued_until_cooldown',not_before_utc=review['not_before_utc'],intent_id=identity,csv_sha256=csv_sha)
 while datetime.now(timezone.utc)<deadline:
  if (P/'CANCEL_SUBMISSION').exists():state('cancelled_before_dispatch');return
  time.sleep(min(10,max(.1,(deadline-datetime.now(timezone.utc)).total_seconds())))
 if (P/'CANCEL_SUBMISSION').exists():state('cancelled_before_dispatch');return
 ledger=Path(review['ledger']);attempt=ledger/'attempts'/csv_sha
 if attempt.exists():
  # Restart may observe a prior dispatch. Never resend it, even if receipt is absent.
  receipt=json.loads((attempt/'receipt.json').read_text()) if (attempt/'receipt.json').exists() else {'status':'unknown'}
 else:
  from huggingface_hub import HfApi
  info=HfApi(token=False).space_info('openadmet/cyp-challenge');assert info.sha==review['reviewed_space_sha'],'Space source changed; root review required'
  assert datetime.now(timezone.utc)<datetime.fromisoformat(review['challenge_deadline_utc'])
  state('dispatching_once',intent_id=identity,csv_sha256=csv_sha)
  receipt=send_prepared(prepared,ledger)
 state('receipt_'+receipt['status'],receipt_path=str(attempt/'receipt.json'),intent_id=identity,csv_sha256=csv_sha)
 current=json.loads((P/'STATUS.json').read_text());current.update(stage='submission_receipt_'+receipt['status'],submission_not_yet_sent=False,submission_attempted=True,submitted=receipt['status']=='accepted_pending',receipt_file=str(attempt/'receipt.json'));(P/'STATUS.json').write_text(json.dumps(current,indent=2)+'\n')
 if receipt['status']=='accepted_pending':
  (P/'RESULT_RU.md').write_text('# Решение принято, ожидается официальный балл\n\nСервер подтвердил приём нового CSV. Повторной отправки не будет; процесс проверяет появление новой строки с соответствующими временем и названием метода.\n\n[Текущий статус](dispatch-status.json) · [Протокол и модели](REPORT_RU.md).\n')
 if receipt['status']=='rejected':return
 dispatch=json.loads((attempt/'attempt.json').read_text())['dispatched_utc'];end=time.monotonic()+130*60
 while time.monotonic()<end:
  if (P/'CANCEL_SUBMISSION').exists():state('monitor_cancelled_after_dispatch',receipt_status=receipt['status']);return
  try:
   out,result=check(directory,dispatch)
   if result['matches']:
    evidence=out/'result.json';recon={'csv_sha256':csv_sha,'status':'processed','evidence':{'path':str(evidence),'sha256':hashlib.sha256(evidence.read_bytes()).hexdigest()},'matching_fields':['Username','Model Report Link','Submitted >= dispatch minute'],'limitation':'Public board does not expose uploaded-file hash; match complements local immutable intent and receipt.'}
    f=attempt/'reconciliation.json'
    if not f.exists():f.write_text(json.dumps(recon,indent=2)+'\n')
    row=result['matches'][0];reference=result['reference_rows'][0] if result['reference_rows'] else None
    current=json.loads((P/'STATUS.json').read_text());current.update(stage='official_result_available',submission_not_yet_sent=False,submitted=True,new_official_score=float(row['MA-ST-RAE']),official_rank=int(row['Rank']),official_result_file=str(evidence));(P/'STATUS.json').write_text(json.dumps(current,indent=2)+'\n')
    report='# Официальный результат воспроизведения briford\n\n'
    report+=f"Наш новый ST-RAE: **{float(row['MA-ST-RAE']):.6f}**, место **{row['Rank']}**. Меньше ST-RAE — лучше.\n\n"
    if reference:report+=f"briford в том же снимке: **{float(reference['MA-ST-RAE']):.6f}**, место {reference['Rank']}.\n\n"
    report+=f"Первый адаптированный вариант: 0,7521205. Новый файл: `{csv_sha}`.\n\n"
    report+='Это повторное выполнение доступного авторского рецепта с документированными ограничениями исторических данных и окружения; тождество исходным весам не установлено.\n\n'
    report+=f"[Точный снимок результата]({evidence.relative_to(P)}) · [Протокол и модели](REPORT_RU.md).\n"
    (P/'RESULT_RU.md').write_text(report)
    state('official_result_available',result_path=str(evidence),matches=result['matches'],reference_rows=result['reference_rows'],intent_id=identity,csv_sha256=csv_sha);return
   state('accepted_waiting_for_new_result',last_check=str(out/'result.json'),intent_id=identity,csv_sha256=csv_sha)
  except Exception as e:state('read_check_failed_will_retry_read_only',exception_type=type(e).__name__,intent_id=identity)
  time.sleep(180)
 state('official_result_not_visible_after_monitor_deadline',receipt_status=receipt['status'],intent_id=identity,csv_sha256=csv_sha)
if __name__=='__main__':
 try:main()
 except Exception as e:
  state('needs_root_review_no_automatic_retry',exception_type=type(e).__name__);raise
