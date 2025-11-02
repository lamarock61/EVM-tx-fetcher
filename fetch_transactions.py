import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd
from web3 import Web3
from web3.contract import Contract
from eth_typing import ChecksumAddress
from dotenv import load_dotenv
from config import CHAIN_CONFIGS

# Common ABIs
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]

# Known contract signatures
KNOWN_SIGNATURES = {
    '0x095ea7b3': 'approve',
    '0xa9059cbb': 'transfer',
    '0x23b872dd': 'transferFrom',
    '0x70a08231': 'balanceOf',
    '0x18160ddd': 'totalSupply'
}

# Known CEX addresses
CEX_ADDRESSES = {
    '0x28C6c06298d514Db089934071355E5743bf21d60': 'Binance',
    '0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549': 'Binance',
    '0xdAC17F958D2ee523a2206206994597C13D831ec7': 'Tether',
    '0x2FAF487A4414Fe77e2327F0bf4AE2a264a776AD2': 'FTX',
    '0x8958618332Df62AF93053Bb9C96D4C73d6c4M1a': 'Coinbase',
}

# Contract type signatures
CONTRACT_TYPES = {
    '0x5c19a7f': 'DEX',
    '0x2e1a7d4': 'Staking',
    '0x4e71d92': 'NFT Marketplace',
    '0xa0712d6': 'Token Sale',
    '0x1694505': 'Lending',
}

# Load environment variables
load_dotenv()

class TransactionFetcher:
    def __init__(self, chains: List[str] = None, max_transactions: int = None):
        self.wallet_addresses = [addr.strip() for addr in os.getenv('WALLET_ADDRESSES', '').split(',')]
        self.selected_chains = chains if chains else list(CHAIN_CONFIGS.keys())
        self.max_transactions = max_transactions
        self.web3_connections = self._setup_web3_connections()
        
    def _setup_web3_connections(self) -> Dict[str, Web3]:
        """Setup Web3 connections for selected chains"""
        connections = {}
        for chain_name, config in CHAIN_CONFIGS.items():
            if chain_name not in self.selected_chains:
                continue
            project_id = os.getenv('INFURA_PROJECT_ID')
            if not project_id:
                print("Error: INFURA_PROJECT_ID not found in .env file")
                continue
                
            # Try both HTTPS and WSS endpoints
            rpc_url = f"https://mainnet.infura.io/v3/{project_id}"
            wss_url = f"wss://mainnet.infura.io/ws/v3/{project_id}"
            print(f"Using RPC URL: {rpc_url}")
            print(f"Attempting to connect to {config['name']}")
            print(f"Testing connection with a basic request...")
            
            try:
                # Create provider with increased timeout
                provider = Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 30})
                web3 = Web3(provider)
                
                # Try a simple request first
                print("Checking connection...")
                is_connected = web3.is_connected()
                print(f"Connection test result: {is_connected}")
                
                if is_connected:
                    # Try getting network version
                    print("Getting network version...")
                    net_version = web3.net.version
                    print(f"Network version: {net_version}")
                    
                    # Try getting latest block
                    print("Getting latest block...")
                    latest_block = web3.eth.block_number
                    print(f"Latest block: {latest_block}")
                    
                    connections[chain_name] = web3
                    print(f"Successfully connected to {config['name']} (Latest block: {latest_block})")
                else:
                    print(f"Failed to connect to {config['name']} - Connection test failed")
            except Exception as e:
                print(f"Error connecting to {config['name']}:")
                print(f"Detailed error: {str(e)}")
        return connections

    def fetch_transactions(self, start_block: int = None, end_block: int = None) -> pd.DataFrame:
        """Fetch transactions for all configured wallets across all chains"""
        all_transactions = []
        
        for chain_name, web3 in self.web3_connections.items():
            chain_config = CHAIN_CONFIGS[chain_name]
            print(f"\nFetching transactions from {chain_config['name']}...")
            
            if end_block is None:
                end_block = web3.eth.block_number
            if start_block is None:
                # Look back 100,000 blocks (approximately 2 weeks)
                start_block = end_block - 100000
            
            for address in self.wallet_addresses:
                if not web3.is_address(address):
                    print(f"Invalid address format: {address}")
                    continue
                    
                print(f"Processing address: {address}")
                
                # Get transactions for the address using optimized approach
                print(f"Fetching transactions for address: {address}")
                
                try:
                    # Get the latest nonce (number of sent transactions)
                    nonce = web3.eth.get_transaction_count(address)
                    print(f"Account has sent {nonce} transactions")
                    
                    # Get the latest transactions first
                    for block_number in range(end_block, max(start_block, end_block - 1000), -1):
                        try:
                            block = web3.eth.get_block(block_number, full_transactions=True)
                            for tx in block.transactions:
                                if (tx['from'].lower() == address.lower() or 
                                        (tx['to'] and tx['to'].lower() == address.lower())):
                                    tx_data = self._process_transaction(tx, chain_name, address)
                                    all_transactions.append(tx_data)
                                    print(f"Found transaction in block {block_number}: {tx['hash'].hex()}")
                                    
                                    if self.max_transactions and len(all_transactions) >= self.max_transactions:
                                        print(f"Reached maximum transaction limit of {self.max_transactions}")
                                        return pd.DataFrame(all_transactions)
                        except Exception as e:
                            print(f"Error processing block {block_number}: {str(e)}")
                            continue
                                    
                        except Exception as e:
                            print(f"Error processing transaction: {str(e)}")
                            continue
                            
                except Exception as e:
                    print(f"Error fetching transactions: {str(e)}")
                except Exception as e:
                    print(f"Error fetching incoming transactions: {str(e)}")
        
        # Convert to DataFrame
        if all_transactions:
            df = pd.DataFrame(all_transactions)
            return df
        else:
            return pd.DataFrame()

    def _process_transaction(self, tx: Dict, chain_name: str, address: str) -> Dict:
        """Process a single transaction and return formatted data"""
        return {
            'chain': chain_name,
            'hash': tx['hash'].hex(),
            'from': tx['from'],
            'to': tx['to'],
            'value': float(Web3.from_wei(tx['value'], 'ether')),  # Convert to float for SQLite compatibility
            'gas_price': float(Web3.from_wei(tx['gasPrice'], 'gwei')),  # Convert to float
            'block_number': tx['blockNumber'],
            'nonce': tx['nonce'],
            'timestamp': datetime.now().isoformat(),  # You might want to get the actual block timestamp
            'is_outgoing': tx['from'].lower() == address.lower()
        }

    def save_transactions(self, df: pd.DataFrame, output_format: str = 'csv'):
        """Save transactions to a file"""
        if df.empty:
            print("No transactions to save")
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if output_format.lower() == 'csv':
            filename = f'transactions_{timestamp}.csv'
            df.to_csv(filename, index=False)
        else:  # sqlite
            filename = f'transactions_{timestamp}.db'
            import sqlite3
            conn = sqlite3.connect(filename)
            df.to_sql('transactions', conn, if_exists='replace', index=False)
            conn.close()
        
        print(f"Transactions saved to {filename}")

def main():
    # Configuration for Ethereum only with 100 transaction limit
    selected_chains = ['ethereum']  # Only fetch from Ethereum
    max_transactions = 100  # Limit to 100 transactions
    
    # Create TransactionFetcher instance with limits
    fetcher = TransactionFetcher(chains=selected_chains, max_transactions=max_transactions)
    
    # Fetch transactions
    print(f"Fetching up to {max_transactions} transactions from chains: {', '.join(selected_chains)}...")
    transactions_df = fetcher.fetch_transactions()
    
    # Save to both CSV and SQLite for flexibility
    fetcher.save_transactions(transactions_df, 'csv')
    fetcher.save_transactions(transactions_df, 'sqlite')

if __name__ == "__main__":
    main()
