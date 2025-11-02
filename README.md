# Multi-Chain Transaction Fetcher

This Python script allows you to fetch and store transactions from multiple EVM-compatible blockchain networks for specified wallet addresses.

## Features

- Support for multiple EVM chains (Ethereum, Polygon, BSC, Avalanche)
- Fetches both incoming and outgoing transactions
- Stores data in CSV and SQLite formats
- Configurable RPC endpoints and API keys
- Handles multiple wallet addresses

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - Windows:
     ```bash
     .\.venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

3. Install required packages:
   ```bash
   pip install web3 pandas python-dotenv
   ```

4. Configure your `.env` file:
   - Copy the example values from the `.env` file
   - Replace with your actual wallet addresses and API keys

5. Update `config.py` with your preferred RPC endpoints

## Usage

Run the script:
```bash
python fetch_transactions.py
```

The script will:
1. Connect to configured blockchain networks
2. Fetch transactions for specified wallet addresses
3. Save the results in both CSV and SQLite formats

## Output

The script generates two files:
- `transactions_[timestamp].csv`: CSV format for easy viewing in spreadsheet software
- `transactions_[timestamp].db`: SQLite database for more complex querying

## Data Structure

The following transaction data is collected:
- Chain name
- Transaction hash
- From address
- To address
- Value (in native currency)
- Gas price (in Gwei)
- Block number
- Nonce
- Timestamp
- Transaction direction (incoming/outgoing)
