---
name: smoobu-rate-management
description: >-
  Guide and workflow for managing Smoobu PMS daily rates and authenticating with HMAC-SHA256.
  Use when setting or updating prices for Smoobu properties, retrieving API keys/secrets and apartment IDs from the Smoobu UI, or troubleshooting Smoobu API requests.
---

# Smoobu Rate Management & HMAC API Integration

This skill provides step-by-step instructions and references for interacting with the Smoobu PMS API, generating HMAC-SHA256 credentials, locating apartment IDs, and updating daily rates.

---

## 🔑 1. How to Find Credentials in Smoobu UI

### Generating API Key & API Secret
1. Log in to [Smoobu](https://login.smoobu.com).
2. Navigate to **Settings → Advanced → API Keys** (or *Paramètres → Jetons API* in French).
3. Under the **Jetons API** section, click the black **`Créer`** (Create) button on the top right.
4. Provide a name/label for the key (e.g. `Script Tariffe`).
5. Copy both the **`API Key`** (`X-API-Key`) and **`API Secret`**.
   > ⚠️ **IMPORTANT**: The **API Secret** is displayed **only once** upon creation. Store it in a secure password manager or environment variable.

### Locating `APARTMENT_ID`
1. On the same API settings page (**Jetons API**), look at the bottom section labeled **Propriétés** (Properties).
2. Locate your listing name (e.g., *Governo Vecchio 34*).
3. The numeric ID inside the input box next to the listing name is your **`APARTMENT_ID`**.

---

## 🔒 2. HMAC-SHA256 Authentication Protocol

Smoobu requires HMAC authentication on all modern API endpoints (legacy `Api-Key` headers expire October 31, 2026).

### Required HTTP Headers
| Header | Description | Example |
|---|---|---|
| `X-API-Key` | Your API Key | `usr_live_abc123` |
| `X-Timestamp` | UTC ISO 8601 string | `2026-09-30T14:30:00Z` |
| `X-Nonce` | Unique UUID v4 for replay protection | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Signature` | Base64-encoded HMAC-SHA256 signature | `47b5a8...=` |

### Canonical String Structure
```text
METHOD\n
/api/path\n
query_string_or_empty\n
TIMESTAMP\n
NONCE\n
SHA256_HEX(body)\n
API_KEY
```

### Signature Formula
```python
signature = base64.b64encode(
    hmac.new(
        api_secret.encode('utf-8'),
        canonical_string.encode('utf-8'),
        hashlib.sha256
    ).digest()
).decode('utf-8')
```

---

## 📡 3. Rates Endpoint Specification

- **Endpoint**: `POST https://login.smoobu.com/api/rates`
- **Headers**: HMAC headers + `Content-Type: application/json`
- **Request Body**:
```json
{
  "apartments": [12345],
  "operations": [
    {
      "dates": ["2026-11-15"],
      "daily_price": 150.0,
      "min_length_of_stay": 2
    }
  ]
}
```

---

## 🚀 4. Executing the Rate Update Script

Use `smoobu_set_rate.py` located in the project root:

```bash
export API_KEY="usr_live_abc123"
export API_SECRET="your_api_secret_here"
export APARTMENT_ID="12345"
export TARGET_DATE="2026-11-15"
export NEW_PRICE="150.00"

python smoobu_set_rate.py
```

---

## 🐞 5. Troubleshooting Guide

- **`401 Unauthorized`**:
  - Verify `API_KEY` and `API_SECRET`.
  - Check system clock synchronization (must be within ±5 minutes of server time).
  - Ensure canonical string format matches exactly (LF line breaks, hex body hash, correct path).
- **`500 Internal Server Error`**:
  - `Price is required`: Ensure `daily_price` is provided.
  - `invalid Date format`: Ensure date format is strictly `YYYY-MM-DD`.
  - `Apartment not found`: Check that `APARTMENT_ID` belongs to the authenticated account.
