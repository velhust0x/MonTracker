# Standard ERC-20 ABI (minimal for Transfer event)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
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
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": True, "name": "spender", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Approval",
        "type": "event"
    }
]

# Standard ERC-721 ABI (minimal for Transfer event)
ERC721_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "_name", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "_symbol", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_tokenId", "type": "uint256"}],
        "name": "tokenURI",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "_from", "type": "address"},
            {"indexed": True, "name": "_to", "type": "address"},
            {"indexed": True, "name": "_tokenId", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    }
]

# Standard ERC-1155 ABI (minimal for Transfer events)
ERC1155_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "_operator", "type": "address"},
            {"indexed": True, "name": "_from", "type": "address"},
            {"indexed": True, "name": "_to", "type": "address"},
            {"indexed": False, "name": "_id", "type": "uint256"},
            {"indexed": False, "name": "_value", "type": "uint256"}
        ],
        "name": "TransferSingle",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "_operator", "type": "address"},
            {"indexed": True, "name": "_from", "type": "address"},
            {"indexed": True, "name": "_to", "type": "address"},
            {"indexed": False, "name": "_ids", "type": "uint256[]"},
            {"indexed": False, "name": "_values", "type": "uint256[]"}
        ],
        "name": "TransferBatch",
        "type": "event"
    }
]

# Common function signatures for smart contract interactions
FUNCTION_SIGNATURES = {
    "0xa9059cbb": "transfer(address,uint256)",  # ERC20 transfer
    "0x23b872dd": "transferFrom(address,address,uint256)",  # ERC20/721 transferFrom
    "0x095ea7b3": "approve(address,uint256)",  # ERC20 approve
    "0x42842e0e": "safeTransferFrom(address,address,uint256)",  # ERC721 safeTransferFrom
    "0xb88d4fde": "safeTransferFrom(address,address,uint256,bytes)",  # ERC721 safeTransferFrom with data
    "0xf242432a": "safeTransferFrom(address,address,uint256,uint256,bytes)",  # ERC1155 safeTransferFrom
    "0x7ff36ab5": "swapExactETHForTokens(uint256,address[],address,uint256)",  # Uniswap V2 swap
    "0x38ed1739": "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)",  # Uniswap V2 swap tokens
    "0x8803dbee": "swapTokensForExactTokens(uint256,uint256,address[],address,uint256)",  # Uniswap V2 swap
    "0x414bf389": "exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))",  # Uniswap V3
    "0x49404b7c": "exactInput((bytes,address,uint256,uint256,uint256))",  # Uniswap V3
    "0x02751cec": "removeLiquidity(address,address,uint256,uint256,uint256,address,uint256)",  # Remove liquidity
    "0xe8e33700": "addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)",  # Add liquidity
    "0x1249c58b": "stake(uint256)",  # Generic stake
    "0x3d18b912": "unstake(uint256)",  # Generic unstake
    "0x379607f5": "claim()",  # Generic claim
    "0x2e1a7d4d": "withdraw(uint256)",  # Generic withdraw
    "0x095ea7b3": "approve(address,uint256)",  # Approve
}

