# ADMETlab3 web batch access, read-only findings

The captured API cooldown result at2026-10-24T15:12:10.578UTC wasHTTP429 after1.16seconds. Body is169bytes of generic nginx/1.20.1 HTML. There is noRetry-After, WWW-Authenticate, rate-limit, quota, or otherdiagnosticheader. It doesnotestablishIPban, accountquota, ormissingcredentials.

The liveOpenAPI snapshot hasno securityorsecuritySchemes. Officialexamples sendonlyJSONContent-Type. EarlierCCO predictionandCSVlookupbothsucceededwithoutlogin,token,orcookie. The maintainedthird-partyclient canoptionallysendX-API-KEY, butdescribesitasreservedforfutureauth; thatisnotanofficialrequirement. Noauthheader/cookieworkaroundwasattempted.

Official GET https://admetlab3.scbdd.com/server/screening returned200 onthe SAMEhost/IP duringAPI429. Thisdocumentsanordinarywebbatchworkflow:
- textareaform2:POST /server/screeningCal,application/x-www-form-urlencoded;
- fieldsmethod=2,smiles-list=newline-separatedSMILES,csrfmiddlewaretoken;
- same-originDjangoCSRFcookieobtainedbyloadingtheform;
- visiblelimitMAX1000SMILES;
- fileform1:multipartPOSTsameaction,method=1,uploadfile(csv/txt/sdf),is_example=0.

The JavaScript simply submits the form and opens a loadingmodal. No asynchronousjob-pollingAPIisdocumentedintheobservedpage. Read-onlydocumentationquickStartisimagebased. The staticAPIoutputexamplecontainsanolderschema andcannotestablishcurrentwebbatchoutputcompleteness. NoformPOSThadbeenmadeatthisread-onlystage.

webbatch_dryrun.py constructs andvalidatestheformfields OFFLINE andprints onlyredactedmetadata. It sendsnonetworkrequests. It isnot a ratelimitworkaround and doesnotassumethatweboutputrowsareorderedorexhaustive.

RootauthorizedoneAPIpredictionprobe atornotbefore15:57:15UTC (atleast45minafterlast429), sameIPandsamepayload. Ifstill429, root separatelyauthorizedexactlyoneordinarysame-IPCSRFformsubmissionofCCO throughthisdocumentedpublicwebworkflow. NoIProtation, fakeUA, CAPTCHA,authbypass,orbulkrequestsarepermitted. Captureactualresponse/task/downloadlinks; stopon429/accessblock. These probesareboundedoperationalchecks, notmassacquisition.
