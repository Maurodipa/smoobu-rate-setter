#!/usr/bin/env python3
"""
smoobu_get_rates.py
===================
Script autonomo per consultare e leggere le tariffe, la disponibilità e le 
restrizioni di soggiorno per un appartamento specifico su Smoobu.

Autenticazione: HMAC-SHA256 (nuovo standard Smoobu).
Endpoint: GET https://login.smoobu.com/api/rates

Documentazione:
  https://docs.smoobu.com/#get-rates
  https://docs.smoobu.com/#hmac-authentication

Uso rapido:
  python smoobu_get_rates.py

Con variabili d'ambiente:
  API_KEY=... API_SECRET=... APARTMENT_ID=12345 START_DATE=2026-10-01 END_DATE=2026-10-31 python smoobu_get_rates.py
"""

import hmac
import hashlib
import base64
import uuid
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

# ===========================================================================
# CONFIGURAZIONE
# ===========================================================================

API_KEY       = os.environ.get("API_KEY",       "YOUR_API_KEY_HERE")
API_SECRET    = os.environ.get("API_SECRET",    "YOUR_API_SECRET_HERE")
APARTMENT_ID  = int(os.environ.get("APARTMENT_ID", "0"))          # ID alloggio

# Date di default: da oggi a 30 giorni nel futuro
TODAY_STR     = datetime.now(timezone.utc).strftime("%Y-%m-%d")
FUTURE_30     = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")

START_DATE    = os.environ.get("START_DATE",    TODAY_STR)         # Formato YYYY-MM-DD
END_DATE      = os.environ.get("END_DATE",      FUTURE_30)         # Formato YYYY-MM-DD

BASE_URL      = "https://login.smoobu.com"
API_PATH      = "/api/rates"


# ===========================================================================
# FUNZIONI HMAC & CANONICALIZATION
# ===========================================================================

def sha256_hex(data: str) -> str:
    """Calcola l'hash SHA-256 in formato esadecimale lowercase."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_signature(canonical: str, secret: str) -> str:
    """Calcola la firma HMAC-SHA256 e la restituisce in Base64."""
    signature_bytes = hmac.new(
        secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(signature_bytes).decode("utf-8")


def build_hmac_headers(
    method: str,
    path: str,
    query_string: str,
    body_str: str,
    api_key: str,
    api_secret: str,
) -> dict:
    """
    Genera i 4 header HMAC richiesti da Smoobu:
      - X-API-Key
      - X-Timestamp (UTC ISO 8601)
      - X-Nonce (UUID v4)
      - X-Signature (HMAC-SHA256 Base64)
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    nonce     = str(uuid.uuid4())
    body_hash = sha256_hex(body_str)

    # La stringa canonica secondo le specifiche Smoobu
    canonical = "\n".join([
        method.upper(),
        path,
        query_string,
        timestamp,
        nonce,
        body_hash,
        api_key,
    ])

    signature = compute_signature(canonical, api_secret)

    return {
        "X-API-Key":   api_key,
        "X-Timestamp": timestamp,
        "X-Nonce":     nonce,
        "X-Signature": signature,
    }


# ===========================================================================
# FUNZIONI DI API
# ===========================================================================

def get_apartment_info(api_key: str, api_secret: str, apartment_id: int) -> dict:
    """Recupera le informazioni di base sull'appartamento (es. nome, valuta, ecc.)."""
    path = f"/api/apartments/{apartment_id}"
    url = BASE_URL + path
    
    # Body vuoto per GET
    empty_hash = sha256_hex("")
    headers = build_hmac_headers("GET", path, "", "", api_key, api_secret)
    headers["Accept"] = "application/json"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def get_apartment_rates(
    api_key: str,
    api_secret: str,
    apartment_id: int,
    start_date: str,
    end_date: str,
) -> dict:
    """
    Recupera le tariffe e le disponibilità per l'appartamento nel range di date indicato.
    """
    # Validazione input
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        raise ValueError("API_KEY non impostata.")
    if not api_secret or api_secret == "YOUR_API_SECRET_HERE":
        raise ValueError("API_SECRET non impostata.")
    if apartment_id <= 0:
        raise ValueError(f"APARTMENT_ID non valido: {apartment_id}.")

    # I parametri di query devono essere codificati ed ordinati alfabeticamente per la stringa canonica.
    # Esempio parametri: apartments[]=123&end_date=2026-10-31&start_date=2026-10-01
    query_params_dict = {
        "apartments[]": str(apartment_id),
        "end_date": end_date,
        "start_date": start_date,
    }
    
    # Ordiniamo alfabeticamente le chiavi per la canonical string
    sorted_keys = sorted(query_params_dict.keys())
    query_pairs = [f"{quote(k, safe='')}={quote(query_params_dict[k], safe='')}" for k in sorted_keys]
    canonical_query_string = "&".join(query_pairs)

    # Costruiamo gli header HMAC (body vuoto per GET)
    headers = build_hmac_headers(
        method="GET",
        path=API_PATH,
        query_string=canonical_query_string,
        body_str="",
        api_key=api_key,
        api_secret=api_secret,
    )
    headers["Accept"] = "application/json"

    # URL finale per la richiesta HTTP
    full_url = f"{BASE_URL}{API_PATH}?{canonical_query_string}"

    print("=" * 70)
    print("SMOOBU — Lettura Tariffe Appartamento")
    print("=" * 70)
    print(f"  Apartment ID  : {apartment_id}")
    print(f"  Periodo       : Da {start_date} a {end_date}")
    print(f"  Endpoint      : GET {full_url}")
    print("-" * 70)

    response = requests.get(full_url, headers=headers, timeout=30)

    if response.status_code == 200:
        result = response.json()
        return result

    elif response.status_code == 401:
        print("\n🔴 ERRORE 401 — Autenticazione fallita.")
        print("   Verifica che API_KEY e API_SECRET siano corrette.")
        response.raise_for_status()

    elif response.status_code == 500:
        print(f"\n🔴 ERRORE 500 — Errore del server Smoobu: {response.text}")
        response.raise_for_status()

    else:
        print(f"\n🔴 ERRORE HTTP {response.status_code}: {response.text}")
        response.raise_for_status()

    return {}


def print_rates_summary(rates_data: dict, apartment_id: int, apt_info: dict = None):
    """Formatta e stampa a schermo le tariffe ricevute da Smoobu."""
    data = rates_data.get("data", {})
    apt_rates = data.get(str(apartment_id), {})

    currency = "EUR"
    if apt_info and "currency" in apt_info:
        currency = apt_info["currency"]

    if not apt_rates:
        print("⚠️ Nessun dato sulle tariffe trovato per questo periodo.")
        return

    print(f"\n📊 TARIFFE E DISPONIBILITÀ PER APPARTAMENTO {apartment_id}")
    if apt_info and "name" in apt_info:
        print(f"   Nome Alloggio: {apt_info.get('name')}")
    print("-" * 70)
    print(f"{'Data':<12} | {'Prezzo (' + currency + ')':<12} | {'Min Notti':<12} | {'Disponibile':<12}")
    print("-" * 70)

    for date_str in sorted(apt_rates.keys()):
        day_info = apt_rates[date_str]
        price = day_info.get("price")
        price_str = f"€{price:.2f}" if price is not None else "N/D"
        
        min_stay = day_info.get("min_length_of_stay")
        min_stay_str = str(min_stay) if min_stay is not None else "-"
        
        avail = day_info.get("available")
        avail_str = "✅ Sì" if avail == 1 else "❌ No"

        print(f"{date_str:<12} | {price_str:<12} | {min_stay_str:<12} | {avail_str:<12}")

    print("=" * 70)


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main():
    try:
        rates_res = get_apartment_rates(
            api_key=API_KEY,
            api_secret=API_SECRET,
            apartment_id=APARTMENT_ID,
            start_date=START_DATE,
            end_date=END_DATE,
        )

        apt_info = get_apartment_info(API_KEY, API_SECRET, APARTMENT_ID)
        print_rates_summary(rates_res, APARTMENT_ID, apt_info)
        return 0

    except ValueError as e:
        print(f"\n🔴 Errore di configurazione: {e}", file=sys.stderr)
        return 1
    except requests.exceptions.HTTPError as e:
        print(f"\n🔴 Errore durante la richiesta API: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n🔴 Errore imprevisto: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
