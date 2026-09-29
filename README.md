# Smoobu Rate Setter 🏠

Script Python per impostare o aggiornare la **tariffa giornaliera** (`daily_price`) di un appartamento specifico su [Smoobu](https://www.smoobu.com) tramite le API ufficiali, con autenticazione **HMAC-SHA256** (nuovo standard).

> ⚠️ Le vecchie API Key (`Api-Key` header) **scadono il 31 ottobre 2026**. Questo script usa già il nuovo sistema HMAC.

---

## 📋 Requisiti

- Python 3.8+
- Libreria `requests`

```bash
pip install requests
```

---

## 🔑 Configurazione

### 1. Ottieni le credenziali API su Smoobu

1. Accedi a [Smoobu](https://login.smoobu.com)
2. Vai su **Settings → Advanced → API Keys**
3. Clicca **Create API Key** e scegli un'etichetta
4. Usa il pulsante **Generate Secret** per creare l'API secret
5. **Copia sia l'API Key che l'API Secret** — il secret è mostrato solo una volta!

### 2. Trova il tuo Apartment ID

Puoi recuperarlo dall'URL nella dashboard Smoobu oppure tramite l'API:
```bash
curl -H "X-API-Key: YOUR_KEY" https://login.smoobu.com/api/apartments
```

### 3. Imposta i parametri

**Opzione A — Variabili d'ambiente (raccomandata)**:
```bash
export API_KEY="usr_live_abc123"
export API_SECRET="your_api_secret_here"
export APARTMENT_ID="12345"
export TARGET_DATE="2026-11-15"
export NEW_PRICE="150.00"
python smoobu_set_rate.py
```

**Opzione B — Modifica diretta nello script**:

Apri `smoobu_set_rate.py` e modifica la sezione CONFIGURAZIONE:
```python
API_KEY       = "usr_live_abc123"
API_SECRET    = "your_api_secret_here"
APARTMENT_ID  = 12345
TARGET_DATE   = "2026-11-15"
NEW_PRICE     = 150.00
```

---

## 🚀 Esecuzione

```bash
python smoobu_set_rate.py
```

**Output di esempio (successo)**:
```
============================================================
SMOOBU — Impostazione tariffa giornaliera
============================================================
  Apartment ID  : 12345
  Data          : 2026-11-15
  Nuova tariffa : €150.00
  Endpoint      : POST https://login.smoobu.com/api/rates
  Timestamp     : 2026-09-29T23:30:00Z
  Nonce         : 550e8400-e29b-41d4-a716-446655440000
  Payload       : {"apartments":[12345],"operations":[{"dates":["2026-11-15"],"daily_price":150.0}]}
------------------------------------------------------------
  HTTP Status   : 200
  Risposta raw  : {"success":true}
============================================================
✅ Tariffa aggiornata con successo!
```

---

## 🔒 Come funziona l'autenticazione HMAC

Ogni richiesta include quattro header speciali:

| Header | Descrizione |
|--------|-------------|
| `X-API-Key` | La tua API Key |
| `X-Timestamp` | Data/ora UTC ISO 8601 (es. `2026-04-01T12:00:00Z`) |
| `X-Nonce` | UUID v4 univoco per ogni richiesta |
| `X-Signature` | Firma HMAC-SHA256 in Base64 |

**Stringa canonica firmata**:
```
METHOD\n
/api/path\n
query_params_or_empty\n
TIMESTAMP\n
NONCE\n
SHA256_HEX(body)\n
API_KEY
```

La firma viene calcolata come:
```python
signature = base64(HMAC-SHA256(canonical_string, api_secret))
```

---

## 🐞 Troubleshooting

### ❌ Errore 401 — Unauthorized

| Causa | Soluzione |
|-------|-----------|
| API Key o Secret errati | Verifica le credenziali in Settings → Advanced → API Keys |
| Timestamp scaduto (> 5 min) | Assicurati che l'orologio di sistema sia sincronizzato (NTP) |
| Nonce già usato | Non dovrebbe accadere — ogni chiamata genera un nuovo UUID v4 |
| Firma HMAC errata | Lo script stampa la stringa canonica riga per riga per il debug |

### ❌ Errore 500 — Internal Server Error

| Messaggio | Causa |
|-----------|-------|
| `"Price is required"` | Il campo `daily_price` è assente |
| `"invalid Date format"` | La data non è in formato `YYYY-MM-DD` |
| `"Apartment not found for this user"` | L'`APARTMENT_ID` non appartiene al tuo account |

### ❌ Errore di connessione

Verifica la tua connessione internet e che `login.smoobu.com` sia raggiungibile.

---

## 📐 Struttura del payload

```json
{
  "apartments": [12345],
  "operations": [
    {
      "dates": ["2026-11-15"],
      "daily_price": 150.0
    }
  ]
}
```

Puoi anche usare **range di date** con il formato `"YYYY-MM-DD:YYYY-MM-DD"`:
```json
{
  "apartments": [12345],
  "operations": [
    {
      "dates": ["2026-11-01:2026-11-07", "2026-11-15"],
      "daily_price": 150.0,
      "min_length_of_stay": 2
    }
  ]
}
```

---

## 📁 Struttura del progetto

```
Smoobu/
├── smoobu_set_rate.py   # Script principale
└── README.md            # Questa documentazione
```

---

## 📜 Riferimenti

- [Smoobu API Documentation — POST Rates](https://docs.smoobu.com/#post-rates-api)
- [Smoobu API Documentation — HMAC Authentication](https://docs.smoobu.com/#hmac-authentication)
- [RFC 3986 — URI Generic Syntax](https://datatracker.ietf.org/doc/html/rfc3986)

---

## 📄 Licenza

MIT License — libero di usare, modificare e distribuire.
