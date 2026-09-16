# my-home

Local web app for managing home-related expenses (materials and services).

## Requirements

- Python 3.10+ (stdlib only — no `pip install`)

## Quick start

**Windows**

```bat
start.bat
```

**macOS / Linux**

```bash
chmod +x start.sh
./start.sh
```

This starts a local server on `http://127.0.0.1:8768/` and opens it in your default browser.

You can also run the server directly:

```bash
python python/expense_server.py --open
```

## Data

All expenses are stored in [`data/expenses.csv`](data/expenses.csv) inside this repository. The file is created and seeded automatically on first run if missing or empty.

### Schema

| Column        | Description                          |
| ------------- | ------------------------------------ |
| `id`          | `EXP_0001` style identifier          |
| `phase`       | Phase (e.g. Pré-compra, Manutenção)  |
| `priority`    | Priority / group (`1`, `2`, or `3`)  |
| `category`    | Category (e.g. Material, Cartório)   |
| `description` | Free-text description                |
| `value`       | Amount in BRL                        |
| `created_at`  | Creation timestamp                   |
| `updated_at`  | Last update timestamp                |

## API

| Method   | Path                  | Purpose                |
| -------- | --------------------- | ---------------------- |
| `GET`    | `/health`             | Health check           |
| `GET`    | `/api/state`          | List expenses + totals |
| `POST` | `/api/expenses`       | Create or update       |
| `DELETE` | `/api/expenses/{id}`  | Delete                 |


## Sync to GitHub

Expense edits are saved locally to data/expenses.csv immediately. Use **Salvar e enviar** in the UI (or POST /api/push) to commit that file and push to origin.



## Dashboard and price import

- Landing view: **Dashboard** (phase timeline + materials).
- **Despesas**: full CRUD (local CSV).
- **Precos / Import**: generate a web-search prompt for an external AI, paste/upload PRICE_PACK.txt, preview, confirm, or download PRICE_AI_FIX.txt for the correction loop.

### Pack contract

Canonical pack: PRICE_PACK.txt with markers ===PREVIEW=== / ===FILE: PRICE_PACK.csv===.

CSV headers: id,description,unit_price,quantity,unit,vendor,product_url,price_notes,value

APIs: POST /api/prompts/price-discovery, POST /api/import/preview, POST /api/import/commit.

## Layout

```
my-home/
  start.bat / start.sh
  data/expenses.csv
  python/expense_server.py
  python/expense_store.py
  web/index.html
  web/styles.css
  web/app.js
```
