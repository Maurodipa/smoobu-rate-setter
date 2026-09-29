#!/usr/bin/env python3
"""
smoobu_set_rate.py
==================
Script per impostare (o aggiornare) la tariffa giornaliera (daily_price)
per un appartamento specifico su Smoobu tramite le API ufficiali.

Autenticazione: HMAC-SHA256 (nuovo standard, sostituisce la legacy Api-Key).
Endpoint: POST https://login.smoobu.com/api/rates

Documentazione:
  https://docs.smoobu.com/#post-rates-api
  https://docs.smoobu.com/#hmac-authentication

Uso rapido:
  python smoobu_set_rate.py

Oppure con variabili d'ambiente:
  API_KEY=... API_SECRET=... APARTMENT_ID=... TARGET_DATE=2026-10-15 NEW_PRICE=120 python smoobu_set_rate.py
"""

import hmac
import hashlib
import base64
import uuid
import json
import os
import sys
from datetime import datetime, timezone

import requests

# ===========================================================================
# CONFIGURAZIONE — modifica questi valori oppure imposta le variabili d'ambiente
# ===========================================================================

API_KEY       = os.environ.get("API_KEY",       "YOUR_API_KEY_HERE")
API_SECRET    = os.environ.get("API_SECRET",    "YOUR_API_SECRET_HERE")
APARTMENT_ID  = int(os.environ.get("APARTMENT_ID", "0"))          # es. 398
TARGET_DATE   = os.environ.get("TARGET_DATE",   "2026-10-15")     # formato YYYY-MM-DD
NEW_PRICE     = float(os.environ.get("NEW_PRICE", "100.00"))      # tariffa giornaliera

# ===========================================================================
# ENDPOINT
# ===========================================================================

BASE_URL  = "https://login.smoobu.com"
API_PATH  = "/api/rates"
FULL_URL  = BASE_URL + API_PATH


# ===========================================================================
# FUNZIONI HMAC
# ===========================================================================

def sha256_hex(data: str) -> str:
    """Calcola il digest SHA-256 di una stringa e lo restituisce in hex."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def build_canonical_string(
    method: str,
    path: str,
    query_string: str,
    timestamp: str,
    nonce: str,
    body_hash: str,
    api_key: str,
) -> str:
    """
    Costruisce la stringa canonica per la firma HMAC secondo la documentazione Smoobu:

        METHOD\\n
        /api/path\\n
        query_string_or_empty\\n
        TIMESTAMP\\n
        NONCE\\n
        BODY_HASH\\n
        API_KEY

    Per richieste POST senza query string, la riga dei parametri è vuota.
    """
    return "\n".join([
        method.upper(),
        path,
        query_string,   # vuoto per POST /api/rates
        timestamp,
        nonce,
        body_hash,
        api_key,
    ])


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
    body_json: str,
    api_key: str,
    api_secret: str,
    query_string: str = "",
) -> dict:
    """
    Genera i quattro header HMAC richiesti da Smoobu:
      - X-API-Key
      - X-Timestamp   (UTC ISO 8601, es. "2026-04-01T12:00:00Z")
      - X-Nonce       (UUID v4)
      - X-Signature   (HMAC-SHA256 in Base64)

    Il body viene hashato con SHA-256 (hex lowercase) prima di essere
    incluso nella stringa canonica.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    nonce     = str(uuid.uuid4())
    body_hash = sha256_hex(body_json)

    canonical = build_canonical_string(
        method=method,
        path=path,
        query_string=query_string,
        timestamp=timestamp,
        nonce=nonce,
        body_hash=body_hash,
        api_key=api_key,
    )

    signature = compute_signature(canonical, api_secret)

    return {
        "X-API-Key":   api_key,
        "X-Timestamp": timestamp,
        "X-Nonce":     nonce,
        "X-Signature": signature,
    }


# ===========================================================================
# FUNZIONE PRINCIPALE
# ===========================================================================

def set_daily_rate(
    api_key: str,
    api_secret: str,
    apartment_id: int,
    target_date: str,
    new_price: float,
) -> dict:
    """
    Imposta la tariffa giornaliera per un appartamento in una data specifica.

    Args:
        api_key:      Chiave API Smoobu.
        api_secret:   Segreto API Smoobu (usato per HMAC).
        apartment_id: ID dell'appartamento su Smoobu.
        target_date:  Data target nel formato YYYY-MM-DD.
        new_price:    Nuova tariffa giornaliera (float).

    Returns:
        Dizionario con la risposta JSON di Smoobu.

    Raises:
        ValueError:  Se i parametri obbligatori non sono validi.
        requests.HTTPError: Se la risposta HTTP indica un errore.
    """
    # --- Validazione input ---
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        raise ValueError("API_KEY non configurata. Imposta la variabile d'ambiente API_KEY o modifica lo script.")
    if not api_secret or api_secret == "YOUR_API_SECRET_HERE":
        raise ValueError("API_SECRET non configurata. Imposta la variabile d'ambiente API_SECRET o modifica lo script.")
    if apartment_id <= 0:
        raise ValueError(f"APARTMENT_ID non valido: {apartment_id}. Deve essere un intero positivo.")
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"TARGET_DATE non valida: '{target_date}'. Usa il formato YYYY-MM-DD.")
    if new_price < 0:
        raise ValueError(f"NEW_PRICE non valido: {new_price}. Deve essere un numero non negativo.")

    # --- Costruzione del payload ---
    # La data può essere specificata come singola data ("YYYY-MM-DD") oppure come
    # range ("YYYY-MM-DD:YYYY-MM-DD"). Qui usiamo la singola data.
    payload = {
        "apartments": [apartment_id],
        "operations": [
            {
                "dates": [target_date],
                "daily_price": new_price,
            }
        ],
    }

    body_json = json.dumps(payload, separators=(",", ":"))  # JSON compatto, senza spazi extra

    # --- Generazione header HMAC ---
    hmac_headers = build_hmac_headers(
        method="POST",
        path=API_PATH,
        body_json=body_json,
        api_key=api_key,
        api_secret=api_secret,
    )

    headers = {
        **hmac_headers,
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }

    # --- Debug info (utile per il troubleshooting) ---
    print("=" * 60)
    print("SMOOBU — Impostazione tariffa giornaliera")
    print("=" * 60)
    print(f"  Apartment ID  : {apartment_id}")
    print(f"  Data          : {target_date}")
    print(f"  Nuova tariffa : €{new_price:.2f}")
    print(f"  Endpoint      : POST {FULL_URL}")
    print(f"  Timestamp     : {hmac_headers['X-Timestamp']}")
    print(f"  Nonce         : {hmac_headers['X-Nonce']}")
    print(f"  Payload       : {body_json}")
    print("-" * 60)

    # --- Invio della richiesta ---
    response = requests.post(
        FULL_URL,
        headers=headers,
        data=body_json,
        timeout=30,
    )

    # --- Gestione della risposta ---
    print(f"  HTTP Status   : {response.status_code}")
    print(f"  Risposta raw  : {response.text}")
    print("=" * 60)

    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print("✅ Tariffa aggiornata con successo!")
        else:
            print("⚠️  La richiesta è andata a buon fine ma 'success' è False.")
        return result

    elif response.status_code == 401:
        print("\n🔴 ERRORE 401 — Autenticazione fallita.")
        print("   Possibili cause:")
        print("   • API_KEY o API_SECRET errati")
        print("   • Timestamp scaduto (> 5 minuti di differenza con il server)")
        print("   • Nonce già usato (non dovrebbe accadere con UUID v4 ogni richiesta)")
        print("   • Firma HMAC calcolata in modo errato")
        print("\n   DEBUG — Stringa canonica usata per la firma:")
        body_hash = sha256_hex(body_json)
        canonical = build_canonical_string(
            method="POST",
            path=API_PATH,
            query_string="",
            timestamp=hmac_headers["X-Timestamp"],
            nonce=hmac_headers["X-Nonce"],
            body_hash=body_hash,
            api_key=api_key,
        )
        for i, line in enumerate(canonical.split("\n")):
            print(f"   Riga {i}: {repr(line)}")
        response.raise_for_status()

    elif response.status_code == 500:
        print(f"\n🔴 ERRORE 500 — Errore interno del server Smoobu.")
        try:
            err = response.json()
            print(f"   Dettaglio: {err.get('detail', 'N/A')}")
        except Exception:
            pass
        response.raise_for_status()

    else:
        print(f"\n🔴 ERRORE HTTP {response.status_code}")
        response.raise_for_status()

    return {}


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main():
    """Punto di ingresso principale dello script."""
    try:
        result = set_daily_rate(
            api_key=API_KEY,
            api_secret=API_SECRET,
            apartment_id=APARTMENT_ID,
            target_date=TARGET_DATE,
            new_price=NEW_PRICE,
        )
        return 0

    except ValueError as e:
        print(f"\n🔴 Errore di configurazione: {e}", file=sys.stderr)
        return 1

    except requests.exceptions.ConnectionError as e:
        print(f"\n🔴 Errore di connessione: impossibile raggiungere Smoobu.\n   {e}", file=sys.stderr)
        return 1

    except requests.exceptions.Timeout:
        print("\n🔴 Timeout: la richiesta ha impiegato troppo tempo.", file=sys.stderr)
        return 1

    except requests.exceptions.HTTPError as e:
        print(f"\n🔴 Errore HTTP: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\n🔴 Errore imprevisto: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
