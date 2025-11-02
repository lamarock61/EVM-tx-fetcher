import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd
from web3 import Web3
from web3.contract import Contract
from eth_abi.codec import ABICodec
from eth_utils import to_checksum_address
import requests
from dotenv import load_dotenv
from constants import CHAIN_CONFIGS, ERC20_ABI, CEX_ADDRESSES, CONTRACT_TYPES, TRANSACTION_TYPES

class TransactionAnalyzer:
    def __init__(self, chain: str, web3: Web3, explorer_api_key: Optional[str] = None):
        self.chain = chain
        self.web3 = web3
        self.explorer_api_key = explorer_api_key
        self.contract_cache = {}
        self.token_cache = {}
        
    def get_contract_info(self, address: str) -> Dict:
        """Get detailed information about a contract"""
        if address in self.contract_cache:
            return self.contract_cache[address]
            
        try:
            # Try to get contract info from explorer API
            api_url = f"{CHAIN_CONFIGS[self.chain]['explorer_api']}"
            params = {
                'module': 'contract',
                'action': 'getsourcecode',
                'address': address,
                'apikey': self.explorer_api_key
            }
            response = requests.get(api_url, params=params)
            data = response.json()
            
            if data['status'] == '1' and data['result'][0].get('ContractName'):
                contract_info = {
                    'name': data['result'][0]['ContractName'],
                    'verified': True,
                    'type': self._determine_contract_type(data['result'][0])
                }
            else:
                # Try to determine if it's an ERC20 token
                contract = self.web3.eth.contract(address=address, abi=ERC20_ABI)
                try:
                    symbol = contract.functions.symbol().call()
                    contract_info = {
                        'name': symbol,
                        'verified': False,
                        'type': 'token'
                    }
                except:
                    contract_info = {
                        'name': 'Unknown Contract',
                        'verified': False,
                        'type': 'unknown'
                    }
            
            self.contract_cache[address] = contract_info
            return contract_info
        except Exception as e:
            print(f"Error getting contract info for {address}: {str(e)}")
            return {'name': 'Unknown', 'verified': False, 'type': 'unknown'}
            
    def _determine_contract_type(self, contract_data: Dict) -> str:
        """Determine the type of contract based on its source code and name"""
        contract_name = contract_data['ContractName'].lower()
        source_code = contract_data.get('SourceCode', '').lower()
        
        for contract_type, keywords in CONTRACT_TYPES.items():
            for keyword in keywords:
                if keyword.lower() in contract_name or keyword.lower() in source_code:
                    return contract_type
                    
        return 'unknown'
        
    def get_token_transfers(self, tx_hash: str) -> List[Dict]:
        """Get all token transfers in a transaction"""
        try:
            receipt = self.web3.eth.get_transaction_receipt(tx_hash)
            transfers = []
            
            for log in receipt['logs']:
                if len(log['topics']) == 3 and log['topics'][0].hex() == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
                    # This is an ERC20 or ERC721 transfer event
                    token_address = log['address']
                    from_addr = '0x' + log['topics'][1].hex()[-40:]
                    to_addr = '0x' + log['topics'][2].hex()[-40:]
                    value = int(log['data'], 16)
                    
                    token_info = self._get_token_info(token_address)
                    
                    transfers.append({
                        'token_address': token_address,
                        'token_symbol': token_info['symbol'],
                        'token_decimals': token_info['decimals'],
                        'from': from_addr,
                        'to': to_addr,
                        'value': value / (10 ** token_info['decimals']) if token_info['decimals'] > 0 else value,
                        'token_type': token_info['type']
                    })
                    
            return transfers
        except Exception as e:
            print(f"Error getting token transfers for {tx_hash}: {str(e)}")
            return []
            
    def _get_token_info(self, address: str) -> Dict:
        """Get token information from contract"""
        if address in self.token_cache:
            return self.token_cache[address]
            
        try:
            contract = self.web3.eth.contract(address=address, abi=ERC20_ABI)
            try:
                symbol = contract.functions.symbol().call()
                decimals = contract.functions.decimals().call()
                token_type = 'ERC20'
            except:
                symbol = 'UNKNOWN'
                decimals = 0
                token_type = 'ERC721'
                
            token_info = {
                'symbol': symbol,
                'decimals': decimals,
                'type': token_type
            }
            self.token_cache[address] = token_info
            return token_info
        except Exception as e:
            print(f"Error getting token info for {address}: {str(e)}")
            return {'symbol': 'UNKNOWN', 'decimals': 0, 'type': 'unknown'}
            
    def classify_transaction(self, tx_hash: str, tx_receipt: Dict) -> str:
        """Classify the type of transaction"""
        # Check for token transfers
        if len(self.get_token_transfers(tx_hash)) > 0:
            return 'token_transfer'
            
        # Check contract interaction
        if tx_receipt['to']:
            contract_info = self.get_contract_info(tx_receipt['to'])
            if contract_info['type'] in CONTRACT_TYPES:
                return contract_info['type'].lower()
                
        return 'unknown'
        
    def is_cex_address(self, address: str) -> Tuple[bool, str]:
        """Check if an address belongs to a known CEX"""
        if self.chain in CEX_ADDRESSES and address.lower() in [addr.lower() for addr in CEX_ADDRESSES[self.chain]]:
            cex_name = CEX_ADDRESSES[self.chain][address]
            return True, cex_name
        return False, ''

class DetailedTransactionFetcher:
    def __init__(self, chains: List[str] = None, max_transactions: int = None):
        load_dotenv()
        self.wallet_addresses = [addr.strip() for addr in os.getenv('WALLET_ADDRESSES', '').split(',')]
        self.selected_chains = chains if chains else list(CHAIN_CONFIGS.keys())
        self.max_transactions = max_transactions
        self.web3_connections = {}
        self.analyzers = {}
        self._setup_connections()
        
    def _setup_connections(self):
        """Setup Web3 connections and analyzers for each chain"""
        for chain_name in self.selected_chains:
            config = CHAIN_CONFIGS[chain_name]
            if 'infura.io' in config['rpc_url']:
                rpc_url = config['rpc_url'].format(project_id=os.getenv('INFURA_PROJECT_ID'))
            else:
                rpc_url = config['rpc_url']
                
            try:
                web3 = Web3(Web3.HTTPProvider(rpc_url))
                if web3.is_connected():
                    self.web3_connections[chain_name] = web3
                    self.analyzers[chain_name] = TransactionAnalyzer(
                        chain_name, 
                        web3,
                        os.getenv(f"{chain_name.upper()}_EXPLORER_API_KEY")
                    )
                    print(f"Successfully connected to {config['name']}")
                else:
                    print(f"Failed to connect to {config['name']}")
            except Exception as e:
                print(f"Error connecting to {config['name']}: {str(e)}")
                
    def fetch_detailed_transactions(self, start_block: int = None, end_block: int = None) -> pd.DataFrame:
        """Fetch detailed transaction information"""
        all_transactions = []
        import time
        
        for chain_name, web3 in self.web3_connections.items():
            analyzer = self.analyzers[chain_name]
            
            if end_block is None:
                end_block = web3.eth.block_number
            if start_block is None:
                start_block = max(0, end_block - 100000)  # Look back ~2 weeks
                
            for address in self.wallet_addresses:
                if not web3.is_address(address):
                    print(f"Invalid address format: {address}")
                    continue
                    
                print(f"Processing {chain_name} address: {address}")
                
                # Process recent blocks with rate limiting
                request_delay = 0.2  # Start with 200ms delay
                
                for block_num in range(end_block, start_block - 1, -1):
                    time.sleep(request_delay)  # Add delay between requests
                    
                    try:
                        block = web3.eth.get_block(block_num, full_transactions=True)
                        timestamp = datetime.fromtimestamp(block['timestamp'])
                        
                        for tx in block.transactions:
                            if (tx['from'].lower() == address.lower() or 
                                (tx['to'] and tx['to'].lower() == address.lower())):
                                time.sleep(0.1)  # Small delay between transaction requests
                                
                                receipt = web3.eth.get_transaction_receipt(tx['hash'])
                                
                                # Get detailed transaction info
                                tx_data = self._process_detailed_transaction(
                                    tx, receipt, chain_name, address, analyzer, timestamp
                                )
                                
                                all_transactions.append(tx_data)
                                print(f"Found transaction: {tx['hash'].hex()}")
                                
                                if self.max_transactions and len(all_transactions) >= self.max_transactions:
                                    return pd.DataFrame(all_transactions)
                                    
                    except Exception as e:
                        error_msg = str(e)
                        print(f"Error processing block {block_num}: {error_msg}")
                        
                        if "Too Many Requests" in error_msg:
                            # Increase delay on rate limit
                            request_delay = min(60, request_delay * 2)
                            print(f"Rate limit hit, increasing delay to {request_delay}s")
                            time.sleep(10)  # Additional cooldown
                        continue
                        
        return pd.DataFrame(all_transactions) if all_transactions else pd.DataFrame()
        
    def _process_detailed_transaction(
        self, tx: Dict, receipt: Dict, chain_name: str, 
        address: str, analyzer: TransactionAnalyzer, timestamp: datetime
    ) -> Dict:
        """Process a single transaction with detailed information"""
        
        # Basic transaction info
        tx_data = {
            'chain': chain_name,
            'hash': tx['hash'].hex(),
            'from': tx['from'],
            'to': tx['to'] if tx['to'] else '',
            'value': float(Web3.from_wei(tx['value'], 'ether')),
            'gas_price': float(Web3.from_wei(tx['gasPrice'], 'gwei')),
            'gas_used': receipt['gasUsed'],
            'block_number': tx['blockNumber'],
            'nonce': tx['nonce'],
            'timestamp': timestamp.isoformat(),
            'is_outgoing': tx['from'].lower() == address.lower(),
            'status': receipt['status']
        }
        
        # Get token transfers
        token_transfers = analyzer.get_token_transfers(tx['hash'])
        if token_transfers:
            tx_data['token_transfers'] = token_transfers
            
        # Classify transaction type
        tx_data['transaction_type'] = analyzer.classify_transaction(tx['hash'], receipt)
        
        # Check for CEX interaction
        is_cex_from, cex_name_from = analyzer.is_cex_address(tx['from'])
        is_cex_to, cex_name_to = analyzer.is_cex_address(tx['to']) if tx['to'] else (False, '')
        
        tx_data['cex_interaction'] = is_cex_from or is_cex_to
        tx_data['cex_name'] = cex_name_from if is_cex_from else cex_name_to
        
        # Get contract information if interacting with a contract
        if tx['to']:
            contract_info = analyzer.get_contract_info(tx['to'])
            tx_data['contract_name'] = contract_info['name']
            tx_data['contract_type'] = contract_info['type']
            
        return tx_data
        
    def save_transactions(self, df: pd.DataFrame, output_format: str = 'csv'):
        """Save transactions to a file"""
        if df.empty:
            print("No transactions to save")
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if output_format.lower() == 'csv':
            filename = f'detailed_transactions_{timestamp}.csv'
            df.to_csv(filename, index=False)
        else:  # sqlite
            filename = f'detailed_transactions_{timestamp}.db'
            import sqlite3
            conn = sqlite3.connect(filename)
            
            # Convert complex columns to JSON strings
            df_copy = df.copy()
            if 'token_transfers' in df_copy.columns:
                df_copy['token_transfers'] = df_copy['token_transfers'].apply(json.dumps)
                
            df_copy.to_sql('transactions', conn, if_exists='replace', index=False)
            conn.close()
            
        print(f"Transactions saved to {filename}")

def main():
    # Example usage with limits and chain selection
    selected_chains = ['ethereum']  # Only fetch from Ethereum
    max_transactions = 1000  # Limit to 1000 transactions
    
    # Set block range
    end_block = 23698712  # Stop at this block
    start_block = end_block - 50000  # Look back 50000 blocks (approximately 1 week)
    
    # Create TransactionFetcher instance with limits
    fetcher = DetailedTransactionFetcher(chains=selected_chains, max_transactions=max_transactions)
    
    # Fetch transactions with specific block range
    print(f"Fetching up to {max_transactions} transactions from blocks {start_block} to {end_block}...")
    transactions_df = fetcher.fetch_detailed_transactions(start_block=start_block, end_block=end_block)
    
    # Save to both CSV and SQLite for flexibility
    fetcher.save_transactions(transactions_df, 'csv')
    fetcher.save_transactions(transactions_df, 'sqlite')

if __name__ == "__main__":
    main()
