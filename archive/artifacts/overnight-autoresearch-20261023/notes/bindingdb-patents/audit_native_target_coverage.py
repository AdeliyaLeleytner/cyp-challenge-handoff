"""Optional remote-only read audit of an already cached native article ZIP.

Usage: python audit_native_target_coverage.py /path/BindingDB_BindingDB_Articles_202610_tsv.zip
No downloads, writes, model execution, or fitting.
"""
import csv,io,json,re,sys,zipfile,collections
path=sys.argv[1]
accessions={'P05177':'CYP1A2','P11712':'CYP2C9','P10635':'CYP2D6','P08684':'CYP3A4'}
pattern=re.compile(r'(?:cyp|cytochrome\s+p450)[\s_-]*(?:1a2|2c9|2d6|3a4)\b',re.I)
counts=collections.Counter();unmatched=collections.Counter()
with zipfile.ZipFile(path) as z:
 names=[n for n in z.namelist() if n.lower().endswith('.tsv')]
 if not names:names=[n for n in z.namelist() if n.lower().endswith('.txt') and 'readme' not in n.lower()]
 assert len(names)==1
 with io.TextIOWrapper(z.open(names[0]),encoding='utf-8-sig',errors='replace') as stream:
  reader=csv.reader(stream,delimiter='\t',quoting=csv.QUOTE_NONE);headers=[x.strip() for x in next(reader)]
  accession_column=next(c for c in headers if c.startswith('UniProt (SwissProt) Primary ID of Target Chain'))
  for values in reader:
   row=dict(zip(headers,values));counts['raw_rows']+=1
   raw=row.get(accession_column,'').strip();a=raw.split()[0] if raw else ''
   name=row.get('Target Name','')
   if a in accessions:counts['exact_accession_rows']+=1
   if pattern.search(name):
    counts['name_hint_rows']+=1
    if a not in accessions:
     counts['name_hint_unmatched_accession_rows']+=1
     unmatched[(name,raw,row.get('Target Source Organism According to Curator or DataSource',''))]+=1
print(json.dumps({'counts':dict(counts),'unmatched_name_hints':[{'target_name':k[0],'raw_accession':k[1],'organism':k[2],'rows':v} for k,v in unmatched.most_common()],
 'interpretation':'Name hints identify possible missed or nonhuman targets; they are not permission to broaden exact-accession training filters.'},indent=2))
