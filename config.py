# EVM Chain configurations
CHAIN_CONFIGS = {
    'ethereum': {
        'rpc_url': 'https://mainnet.infura.io/v3/{project_id}',  # Will be formatted with actual project ID
        'chain_id': 1,
        'name': 'Ethereum Mainnet',
        'network': 'mainnet'  # Adding network identifier
    },
    'polygon': {
        'rpc_url': 'https://polygon-rpc.com',
        'chain_id': 137,
        'name': 'Polygon Mainnet'
    },
    'bsc': {
        'rpc_url': 'https://bsc-dataseed.binance.org/',
        'chain_id': 56,
        'name': 'Binance Smart Chain'
    },
    'avalanche': {
        'rpc_url': 'https://api.avax.network/ext/bc/C/rpc',
        'chain_id': 43114,
        'name': 'Avalanche C-Chain'
    }
}
