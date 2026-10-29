"""Utility functions for the OpenADMET CYP Challenge Gradio app."""

import io
import ipaddress
import re
import socket
import time
from urllib.parse import urljoin, urlparse

import boto3
import pandas as pd
import requests
from config import AWS_DEFAULT_REGION, S3_BUCKET
from loguru import logger

_MAX_REDIRECTS = 5

# S3FS was causing 403 errors in testing on some machines, unclear why.
# Switching to boto3 client which works reliably
s3_client = boto3.client("s3", region_name=AWS_DEFAULT_REGION)

BANNED_USERNAMES = {  # normalized (lowercase) username: reason
    # Team Prescience
    "teamprecience1": "Suspected of using multiple HF accounts",
    "teampresceince-bio": "Suspected of using multiple HF accounts",
    # Reinstated 14 Sep after apologising; re-banned: svk091 submitted TeamPrescience's
    # own structure files (same name, mtime and bytes) on 1 Oct
    "teamprescience": "Suspected of using multiple HF accounts",
    "svk091": "Suspected of using multiple HF accounts",
    "pipl-bio": "Suspected of using multiple HF accounts",
    "teamprescience1": "Suspected of using multiple HF accounts",
    "mark810250": "Suspected of using multiple HF accounts",
    "thecuriousfox": "Suspected of using multiple HF accounts",
    "archasnair": "Suspected of using multiple HF accounts",
    # Safi
    # "safi029": "Suspected of using multiple HF accounts", Apologised, reinstated
    "safi014": "Suspected of using multiple HF accounts",
    # Probing attacks
    # "novice11": "Suspicious entries", Explained, reinstated
    # vaishu / TeamPozeSCAF cluster
    "vaishu53": "Suspected of using multiple HF accounts",
    "vaishnavi53": "Suspected of using multiple HF accounts",
    "vgny": "Suspected of using multiple HF accounts",
    "set12": "Suspected of using multiple HF accounts",
    "vyshug15": "Suspected of using multiple HF accounts",
    "vyshu9966": "Suspected of using multiple HF accounts",
    "gnandini10": "Suspected of using multiple HF accounts",
    "20p1a": "Suspected of using multiple HF accounts",
    "pozescaf": "Suspected of using multiple HF accounts",
    # babulizer cluster
    "babulizer": "Suspected of using multiple HF accounts",
    "babulizer1": "Suspected of using multiple HF accounts",
    "biboba": "Suspected of using multiple HF accounts",
    "biasgod": "Suspected of using multiple HF accounts",
    # happy / sleepq sweep cluster
    "happy01": "Suspected of using multiple HF accounts",
    "happy02": "Suspected of using multiple HF accounts",
    "happy03": "Suspected of using multiple HF accounts",
    "happy04": "Suspected of using multiple HF accounts",
    # perapu cluster
    "peraputeja": "Suspected of using multiple HF accounts",
    "pearpu-babu": "Suspected of using multiple HF accounts",
    "peraputeja5": "Suspected of using multiple HF accounts",
    "21kd1a05e0": "Suspected of using multiple HF accounts",
    "perapu-5e0": "Suspected of using multiple HF accounts",
    "suryaprakashgarbapu123": "Suspected of using multiple HF accounts",
    # Identical predictions across accounts
    # "al0084279": "Suspected of using multiple HF accounts", Reproduced j10b84's public repo, reinstated
    # "j10b84": "Suspected of using multiple HF accounts", Author of the public repo, reinstated
    "c-test": "Suspected of using multiple HF accounts",
    "yanyn": "Suspected of using multiple HF accounts",
    "blue": "Suspected of using multiple HF accounts",
    "test": "Suspected of using multiple HF accounts",
    # JJ cluster (7xkql / q7kp2 / 6jhb4)
    "jjkll111": "Suspected of using multiple HF accounts",
    "jjllff": "Suspected of using multiple HF accounts",
    "uujjkk": "Suspected of using multiple HF accounts",
    # hope cluster (chem17 / qql)
    "hopeful": "Suspected of using multiple HF accounts",
    "hope1": "Suspected of using multiple HF accounts",
    # Daenerys / linda single-compound probe
    "daenerys": "Suspected of using multiple HF accounts",
    "linda": "Suspected of using multiple HF accounts",
    # Game of Thrones / LLLL / Lirq cluster
    "mike": "Suspected of using multiple HF accounts",
    "john": "Suspected of using multiple HF accounts",
    "now": "Suspected of using multiple HF accounts",
    "kael": "Suspected of using multiple HF accounts",
    "music": "Suspected of using multiple HF accounts",
    "bob": "Suspected of using multiple HF accounts",
    "happy": "Suspected of using multiple HF accounts",
    # huang cluster
    "huangzx": "Suspected of using multiple HF accounts",
    "huangsz": "Suspected of using multiple HF accounts",
    "zxhuang": "Suspected of using multiple HF accounts",
    "alisb": "Suspected of using multiple HF accounts",
    "chegan6522": "Suspected of using multiple HF accounts",
    # happyq cluster
    "happyq": "Suspected of using multiple HF accounts",
    "yesorno": "Suspected of using multiple HF accounts",
    "yesoryes": "Suspected of using multiple HF accounts",
    # lex / total cluster (with blue / test)
    "jakewy": "Suspected of using multiple HF accounts",
    "mia": "Suspected of using multiple HF accounts",
    "lgb": "Suspected of using multiple HF accounts",
    "aries": "Suspected of using multiple HF accounts",
    # psk (submitted rasayan-labs' unsubmitted predictions)
    "mzkchem": "Suspected of using multiple HF accounts",
    # samsung / PCA alias-rotation cluster
    "seongseong321": "Suspected of using multiple HF accounts",
    "seong-1241": "Suspected of using multiple HF accounts",
    "sangsung4321": "Suspected of using multiple HF accounts",
    "kmhaonueng": "Suspected of using multiple HF accounts",
    "kingmyqueen": "Suspected of using multiple HF accounts",
    "kori0192": "Suspected of using multiple HF accounts",
    "bomijeong": "Suspected of using multiple HF accounts",
    # jedi / tjumbo paired-submission cluster
    "jetdi-tt": "Suspected of using multiple HF accounts",
    "tjumbo": "Suspected of using multiple HF accounts",
    # Shruti202 / Doraemon14 / Done29 cluster
    "shruti202": "Suspected of using multiple HF accounts",
    "doraemon14": "Suspected of using multiple HF accounts",
    "done29": "Suspected of using multiple HF accounts",
    # cyp450_reg / cyp450_TDI cluster
    "duanbg": "Suspected of using multiple HF accounts",
    "james": "Suspected of using multiple HF accounts",
    "jame": "Suspected of using multiple HF accounts",
    # TIPR / cyp2d6_test alias-series cluster (shared CYP3A4 TDI vector)
    "tipr": "Suspected of using multiple HF accounts",
    "tiprlab": "Suspected of using multiple HF accounts",
    "liux0614": "Suspected of using multiple HF accounts",
    "xiexf": "Suspected of using multiple HF accounts",
    "clawdeen": "Suspected of using multiple HF accounts",
    "gzhgl": "Suspected of using multiple HF accounts",
    "xiangfeixie": "Suspected of using multiple HF accounts",
    # sohu / taobao / jd cluster
    "sohu": "Suspected of using multiple HF accounts",
    "taobao": "Suspected of using multiple HF accounts",
    "jd": "Suspected of using multiple HF accounts",
    # ...and its 12 Oct new-account burst (same recalibrated-pic50 pipeline)
    "hello": "Suspected of using multiple HF accounts",
    "juice": "Suspected of using multiple HF accounts",
    "network": "Suspected of using multiple HF accounts",
    "stone": "Suspected of using multiple HF accounts",
    "drink": "Suspected of using multiple HF accounts",
    "busy": "Suspected of using multiple HF accounts",
    # sub / lac / tab cluster
    "sub": "Suspected of using multiple HF accounts",
    "lac": "Suspected of using multiple HF accounts",
    "tab": "Suspected of using multiple HF accounts",
    # mansi / jith cluster (with balajikola / venkysai123)
    "ce20b010": "Suspected of using multiple HF accounts",
    "cs24m1007alum": "Suspected of using multiple HF accounts",
    "mansi012": "Suspected of using multiple HF accounts",
    "sjithendra": "Suspected of using multiple HF accounts",
    "tejaperapu": "Suspected of using multiple HF accounts",
    "balajikola": "Suspected of using multiple HF accounts",
    "venkysai123": "Suspected of using multiple HF accounts",
    # klekotek cluster
    # "maciejwisniewski": "Suspected of using multiple HF accounts", Apologised, reinstated
    "chairnuch": "Suspected of using multiple HF accounts",
    "gargunec": "Suspected of using multiple HF accounts",
    "temporalloom": "Suspected of using multiple HF accounts",
    # set12 / set21 cluster
    "xgboosting": "Suspected of using multiple HF accounts",
    "set21": "Suspected of using multiple HF accounts",
    "w507": "Suspected of using multiple HF accounts",
    # nyxen cluster
    "alexxi11": "Suspected of using multiple HF accounts",
    "nyxen11": "Suspected of using multiple HF accounts",
    # yourchoice / goodtime cluster (with jake / jackson / yuwang)
    "leo": "Suspected of using multiple HF accounts",
    "sina": "Suspected of using multiple HF accounts",
    "jake": "Suspected of using multiple HF accounts",
    "jackson": "Suspected of using multiple HF accounts",
    "yuwang": "Suspected of using multiple HF accounts",
    # TeamPozeSCAF / scaffold cluster
    "nandini102002": "Suspected of using multiple HF accounts",
    "ojas45": "Suspected of using multiple HF accounts",
    "swathi007": "Suspected of using multiple HF accounts",
    "swathi45": "Suspected of using multiple HF accounts",
    "niteesh2799": "Suspected of using multiple HF accounts",
    # NIPER / omkarpawar cluster
    # "dkdhaked": "Suspected of using multiple HF accounts", Apologised, reinstated
    "sonu12545": "Suspected of using multiple HF accounts",
    "harsh00012": "Suspected of using multiple HF accounts",
    "omkarpawar1": "Suspected of using multiple HF accounts",
    "omkarpawar6699": "Suspected of using multiple HF accounts",
    # clove / ginger shared-alias pair
    "cath598": "Suspected of using multiple HF accounts",
    "catherene98": "Suspected of using multiple HF accounts",
    # 2d6_TDI / 3a4N_TDI pair
    "anna": "Suspected of using multiple HF accounts",
    "lebron": "Suspected of using multiple HF accounts",
    # leebrubeck / wbot pair
    "leebrubeck": "Suspected of using multiple HF accounts",
    # "saulo-acoism": "Suspected of using multiple HF accounts", Apologised, reinstated
    # yg_test / yzlab pair
    "yaowen-gu": "Suspected of using multiple HF accounts",
    "yg3191": "Suspected of using multiple HF accounts",
    # 21kd1a05i7 / Venky0912 / kaggle31x cluster (continuation of perapu / mansi-jith)
    "21kd1a05i7": "Suspected of using multiple HF accounts",
    "teampozescaf": "Suspected of using multiple HF accounts",
    "venky0912": "Suspected of using multiple HF accounts",
    "amilineni": "Suspected of using multiple HF accounts",
    "balaraju02": "Suspected of using multiple HF accounts",
    "kaggle317": "Suspected of using multiple HF accounts",
    "kaggle319": "Suspected of using multiple HF accounts",
    "saibalaji2020": "Suspected of using multiple HF accounts",
    "saisrinu143": "Suspected of using multiple HF accounts",
    "shaunmurphy1": "Suspected of using multiple HF accounts",
    "srikruthi12": "Suspected of using multiple HF accounts",
    # Kevin / NBA / Tom / BNA cluster (test_2d6 / test_TDI / 3a4_TDI)
    "kevin": "Suspected of using multiple HF accounts",
    "nba": "Suspected of using multiple HF accounts",
    "bna": "Suspected of using multiple HF accounts",
    "tom": "Suspected of using multiple HF accounts",
    # GOKUL_202 / ADITI_202 / Rithik_715 threshold sweep (preds_55/65/70)
    "gokul258": "Suspected of using multiple HF accounts",
    "csn202": "Suspected of using multiple HF accounts",
    "rithik715": "Suspected of using multiple HF accounts",
    # wgaussian / lolly / dope / iknos structure pose-pool cluster
    # "wiwnopgm": "Suspected of using multiple HF accounts", Apologised, reinstated
    "nflxthai": "Suspected of using multiple HF accounts",
    "nuk96": "Suspected of using multiple HF accounts",
    "nvith": "Suspected of using multiple HF accounts",
    # Houston / Spur shared CYP3A4 TDI pair
    "houston": "Suspected of using multiple HF accounts",
    "spur": "Suspected of using multiple HF accounts",
    # swathi alias / byte-identical regression trio
    "b22ai083kitsw": "Suspected of using multiple HF accounts",
    "reddyhp": "Suspected of using multiple HF accounts",
    "swaaaaaaaaaa": "Suspected of using multiple HF accounts",
    # submit.csv noise-probing ring
    "bingo": "Suspected of using multiple HF accounts",
    "hfu": "Suspected of using multiple HF accounts",
    "sdw": "Suspected of using multiple HF accounts",
    "dec": "Suspected of using multiple HF accounts",
    # sirty.ai -> coconut-research handover (no cooldown bypass, new account kept)
    "tssiryu": "Suspected of using multiple HF accounts",
    # epoch-checkpoint ring
    "judge": "Suspected of using multiple HF accounts",
    "adapt": "Suspected of using multiple HF accounts",
    "goodman": "Suspected of using multiple HF accounts",
    "tryit": "Suspected of using multiple HF accounts",
    "black": "Suspected of using multiple HF accounts",
    "high": "Suspected of using multiple HF accounts",
    # CHEM_SCI / SCIENCE shared CYP2D6 TDI pair
    "abc258": "Suspected of using multiple HF accounts",
    "arihaan915": "Suspected of using multiple HF accounts",
    # TeamPozeSCAF / srikruthi12 continuation (resubmitted banned members' files)
    "florida06": "Suspected of using multiple HF accounts",
    "nocyp": "Suspected of using multiple HF accounts",
    "srikruthireddy": "Suspected of using multiple HF accounts",
    "srikruthi2005": "Suspected of using multiple HF accounts",
    "chicky03": "Suspected of using multiple HF accounts",
    "rose53": "Suspected of using multiple HF accounts",
    "excuseme2": "Suspected of using multiple HF accounts",
    "stevedustin3": "Suspected of using multiple HF accounts",
    "mightythor09": "Suspected of using multiple HF accounts",
    "sanjana32": "Suspected of using multiple HF accounts",
    # accurate / display / explore / Defend / harmony (last.csv / val.csv ring)
    "accurate": "Suspected of using multiple HF accounts",
    "display": "Suspected of using multiple HF accounts",
    "explore": "Suspected of using multiple HF accounts",
    "defend": "Suspected of using multiple HF accounts",
    "harmony": "Suspected of using multiple HF accounts",
    # gp_screen A/B constant-offset probe pair
    "ajtrx2": "Suspected of using multiple HF accounts",
    "jharrison3502": "Suspected of using multiple HF accounts",
    # Jack / Rocket shared structure poses
    "jack": "Suspected of using multiple HF accounts",
    "rocket": "Suspected of using multiple HF accounts",
    # Rithik715 / CHEM_SCI continuation
    "nanvas123": "Suspected of using multiple HF accounts",
    "sathish": "Suspected of using multiple HF accounts",
    # Resubmitted banned accounts' files (jedi/tjumbo, TIPR, yzlab, yanyn)
    "antsigma": "Suspected of using multiple HF accounts",
    "wpbphysics": "Suspected of using multiple HF accounts",
    "somewhat120": "Suspected of using multiple HF accounts",
    "basedonai": "Suspected of using multiple HF accounts",
    # LGY / Lirq / JJ cluster continuations
    "adam": "Suspected of using multiple HF accounts",
    "linguoyu": "Suspected of using multiple HF accounts",
    "irisq1026": "Suspected of using multiple HF accounts",
    "jjkkll": "Suspected of using multiple HF accounts",
}


def _load_csv_from_s3(key: str, parquet: bool = False) -> pd.DataFrame:
    """Load a CSV file from S3 into a DataFrame."""
    logger.info(f"Downloading from S3: {key}")
    obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
    if parquet:
        return pd.read_parquet(io.BytesIO(obj["Body"].read()))
    return pd.read_csv(io.BytesIO(obj["Body"].read()))


def _safeify_username(username: str) -> str:
    """Sanitise a HuggingFace username for use in S3 keys and file paths.

    HF usernames for organisations use the format ``org/user``, which would create
    unintended S3 path nesting. Spaces are also replaced for safety. Lowercased so
    that HF-username casing variants (which all resolve to the same account) map to
    the same S3 prefix — otherwise the per-user submission cooldown
    (``_fetch_last_submission_date``) could be bypassed by alternating case.
    """
    return str(username.strip()).lower().replace("/", "_").replace(" ", "_")


def _is_safe_public_url(url: str) -> bool:
    """Reject URLs whose host resolves to a private/loopback/link-local address.

    Guards ``check_page_exists`` against SSRF: without this, a user-supplied URL
    (e.g. the "Method Report Link" field) could point the server at internal
    infrastructure and have it echo back reachability.
    """
    hostname = urlparse(url).hostname
    if not hostname:
        return False
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


# TODO: Maybe use Tenacity for retrying?
def check_page_exists(
    url: str,
    delay: float = 0.2,
    max_retries: int = 3,
    current_retries: int = 0,
    restrict_to_public: bool = True,
):
    """Check if a web page exists at the given URL with a retry limit for 429 errors.

    Redirects are followed manually (rather than via ``requests``' built-in
    ``allow_redirects``) so every hop can be checked against
    ``_is_safe_public_url`` before it is requested, closing off SSRF via a
    redirect to an internal address.

    Params:
        url (str): The URL of the page to check.
        delay (float, optional): Seconds to wait until submitting another request.
            Defaults to 0.
        max_retries (int, optional): Maximum number of times to retry on a 429 error.
            Defaults to 3.
        current_retries (int, optional): Current number of retries performed (internal
            counter). Defaults to 0.
        restrict_to_public (bool, optional): Reject hosts that resolve to a
            private/loopback/internal address. Only meaningful protection when
            ``url`` (or its host) is attacker-controlled — e.g. a user-supplied
            link. Should be disabled for calls against a hardcoded, trusted
            domain (e.g. huggingface.co), since some platforms resolve their own
            domain to an internal address for intra-network callers (split-horizon
            DNS), which this check would otherwise incorrectly reject. Defaults to
            True.

    Returns:
        bool: True if the page exists (status code 200), False otherwise.

    """
    safe_url = str(url).strip()

    # Attempt to fix url
    if not safe_url.startswith(("http://", "https://")):
        safe_url = f"https://{safe_url}"

    try:
        response = None
        for _ in range(_MAX_REDIRECTS + 1):
            if restrict_to_public and not _is_safe_public_url(safe_url):
                logger.warning(f"Refusing to fetch non-public URL: {safe_url}")
                return False
            response = requests.get(safe_url, timeout=5, allow_redirects=False)
            if (
                response.status_code in (301, 302, 303, 307, 308)
                and "Location" in response.headers
            ):
                safe_url = urljoin(safe_url, response.headers["Location"])
                continue
            break
        else:
            logger.warning(f"Too many redirects for {url}")
            return False

        # Check for Rate Limit Error and retry if under the limit
        if response.status_code == 429:
            if current_retries < max_retries:
                # Make wait time exponential
                wait_time = 5 * (2**current_retries)
                logger.warning(
                    f"Warning: Rate limit hit on {safe_url}. Attempt "
                    f"{current_retries + 1}/{max_retries}. Waiting for {wait_time} "
                    "seconds..."
                )
                time.sleep(wait_time)
                # Recurse with an incremented retry counter
                return check_page_exists(
                    safe_url,
                    delay=delay,
                    max_retries=max_retries,
                    current_retries=current_retries + 1,
                    restrict_to_public=restrict_to_public,
                )
            else:
                logger.error(
                    f"Error: Max retries ({max_retries}) reached for rate limit on "
                    f"{safe_url}."
                )
                return False  # Give up after max retries

        # Return True only for a successful status code (200)
        return response.status_code == 200

    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking URL {safe_url}: {e}")
        return False

    finally:
        # Sleep after every request to avoid HTTPS error
        time.sleep(delay)


def validate_hf_username(username: str) -> bool:
    """Validate that the Hugging Face username exists by checking the profile page."""
    # restrict_to_public=False: the target here is always the literal huggingface.co
    # domain (hardcoded below, or enforced by the regex above), never an
    # attacker-supplied host, so the SSRF guard in check_page_exists is not needed —
    # and huggingface.co can legitimately resolve to an internal address when called
    # from within HF's own infrastructure (split-horizon DNS), which that guard
    # would otherwise reject.
    if re.match(r"^https?://huggingface\.co/([^/]+)/?$", str(username).strip()):
        return check_page_exists(
            str(username).strip(), delay=1, max_retries=10, restrict_to_public=False
        )
    username = str(username).strip()
    hf_url = f"https://huggingface.co/{username}"
    return check_page_exists(hf_url, delay=1, max_retries=10, restrict_to_public=False)


def validate_model_details(tag: str) -> str:
    """Validate that the model details link is a valid URL and exists."""
    if tag is None or str(tag).strip() == "":
        return "Not submitted"
    safe_tag = str(tag).strip()
    if not safe_tag.startswith("https://"):
        return "Invalid link"
    is_real_url = check_page_exists(safe_tag, delay=2)
    if not is_real_url:
        return "Invalid link"
    else:
        return safe_tag
