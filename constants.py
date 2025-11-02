"""Constants and configurations for the transaction fetcher"""

# Common ABIs
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

# Transaction types
TRANSACTION_TYPES = [
    'token_transfer',
    'token_approval',
    'swap',
    'liquidity_add',
    'liquidity_remove',
    'stake',
    'unstake',
    'claim_rewards',
    'bridge',
    'nft_mint',
    'nft_transfer',
    'airdrop_claim'
]

# Contract types
CONTRACT_TYPES = {
    'DEX': ['Uniswap', 'Sushiswap', 'PancakeSwap'],
    'Lending': ['Aave', 'Compound', 'MakerDAO'],
    'Staking': ['Lido', 'Rocket Pool'],
    'NFT_Marketplace': ['OpenSea', 'LooksRare'],
    'Bridge': ['Polygon Bridge', 'Arbitrum Bridge'],
    'Yield': ['Yearn', 'Curve']
}

# Known CEX addresses
CEX_ADDRESSES = {
    'ethereum': {
        '0x28C6c06298d514Db089934071355E5743bf21d60': 'Binance',
        '0x8958618332Df62AF93053Bb9C96D4C73d6c4M1a': 'Coinbase',
        '0xdAC17F958D2ee523a2206206994597C13D831ec7': 'Tether Treasury',
        '0x2FAF487A4414Fe77e2327F0bf4AE2a264a776AD2': 'FTX'
    }
}

# Chain configurations
CHAIN_CONFIGS = {
    'ethereum': {
        'rpc_url': 'https://mainnet.infura.io/v3/{project_id}',
        'chain_id': 1,
        'name': 'Ethereum Mainnet',
        'explorer_api': 'https://api.etherscan.io/api',
        'explorer_url': 'https://etherscan.io'
    }
}
