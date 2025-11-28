import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from web3 import Web3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from config import (
    TELEGRAM_BOT_TOKEN,
    MONAD_RPC_URL,
    MONAD_CHAIN_ID,
    CHECK_INTERVAL,
    DATABASE_URL
)
from abis import ERC20_ABI, ERC721_ABI, ERC1155_ABI, FUNCTION_SIGNATURES
from database import Database

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(MONAD_RPC_URL))

# Initialize Database
db = Database(DATABASE_URL)


def get_token_info(token_address: str) -> Dict[str, str]:
    """Get token name, symbol, and decimals"""
    try:
        contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        name = contract.functions.name().call()
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        return {"name": name, "symbol": symbol, "decimals": decimals}
    except:
        try:
            contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC721_ABI)
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            return {"name": name, "symbol": symbol, "decimals": 0, "type": "NFT"}
        except:
            return {"name": "Unknown", "symbol": "UNK", "decimals": 18}


def get_function_name(input_data: str) -> str:
    """Get function name from transaction input data"""
    if not input_data or len(input_data) < 10:
        return "Unknown"
    function_signature = input_data[:10]
    return FUNCTION_SIGNATURES.get(function_signature, f"0x{function_signature}")


def format_address(address: str, length: int = 10) -> str:
    """Format address for display"""
    if not address or address == 'Unknown':
        return 'Unknown'
    if len(address) <= length * 2 + 2:
        return address
    return f"{address[:length]}...{address[-8:]}"


def build_section(title: str, rows: List[str]) -> str:
    divider = "────────────────────────────"
    content = "\n".join(rows)
    return f"*{title}*\n{divider}\n{content}\n"


def format_transaction_message(tx_hash: str, tx_data: Dict, wallet_address: str, activity_type: str = "native") -> str:
    """Format sleek transaction message for Telegram"""
    try:
        from_address = tx_data.get('from', 'Unknown')
        to_address = tx_data.get('to', 'Unknown')
        value = tx_data.get('value', 0)
        block_number = tx_data.get('blockNumber', 'N/A')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        direction = "📤 *Sent*" if from_address.lower() == wallet_address.lower() else "📥 *Received*"
        wallet_line = f"{direction} via `{format_address(wallet_address)}`"
        
        header_icon = {
            "native": "🪙",
            "erc20": "💠",
            "erc721": "🖼️",
            "erc1155": "🎨",
            "contract_interaction": "⚙️",
            "contract_deployment": "🏗️"
        }.get(activity_type, "🔔")
        
        sections = []
        sections.append(f"{header_icon} *{activity_type.replace('_', ' ').title()}*")
        sections.append(wallet_line)
        
        tx_rows = [
            f"• *Hash:* `{format_address(tx_hash, 20)}`",
            f"• *Block:* #{block_number}",
        ]
        
        if activity_type == "native":
            value_eth = float(Web3.from_wei(int(value), 'ether')) if isinstance(value, (int, str)) else 0
            tx_rows.extend([
                f"• *From:* `{format_address(from_address)}`",
                f"• *To:* `{format_address(to_address) if to_address != 'Unknown' else 'Contract Creation'}`",
                f"• *Amount:* {value_eth:.6f} MON",
            ])
            sections.append(build_section("Transaction", tx_rows))
        
        elif activity_type == "erc20":
            token_info = tx_data.get('token_info', {})
            token_symbol = token_info.get('symbol', 'TOKEN')
            token_name = token_info.get('name', 'Unknown Token')
            decimals = token_info.get('decimals', 18)
            amount = tx_data.get('amount', 0)
            token_address = tx_data.get('token_address', 'Unknown')
            amount_formatted = float(amount) / (10 ** decimals) if isinstance(amount, (int, str)) else 0
            
            token_rows = [
                f"• *Token:* {token_name}",
                f"• *Symbol:* {token_symbol}",
                f"• *Contract:* `{format_address(token_address)}`"
            ]
            sections.append(build_section("Asset", token_rows))
            tx_rows.append(f"• *Amount:* {amount_formatted:,.6f} {token_symbol}")
            sections.append(build_section("Transfer", tx_rows))
        
        elif activity_type == "erc721":
            token_info = tx_data.get('token_info', {})
            token_symbol = token_info.get('symbol', 'NFT')
            token_name = token_info.get('name', 'Unknown Collection')
            token_id = tx_data.get('token_id', 'N/A')
            token_address = tx_data.get('token_address', 'Unknown')
            
            token_rows = [
                f"• *Collection:* {token_name}",
                f"• *Symbol:* {token_symbol}",
                f"• *Token ID:* #{token_id}",
                f"• *Contract:* `{format_address(token_address)}`"
            ]
            sections.append(build_section("NFT", token_rows))
            sections.append(build_section("Transfer", tx_rows))
        
        elif activity_type == "erc1155":
            token_address = tx_data.get('token_address', 'Unknown')
            token_ids = tx_data.get('token_ids', [])
            amounts = tx_data.get('amounts', [])
            ids_display = ', '.join([f'#{tid}' for tid in token_ids[:5]])
            if len(token_ids) > 5:
                ids_display += f' (+{len(token_ids) - 5} more)'
            amounts_display = ', '.join([str(amt) for amt in amounts[:5]])
            if len(amounts) > 5:
                amounts_display += f' (+{len(amounts) - 5} more)'
            
            token_rows = [
                f"• *Contract:* `{format_address(token_address)}`",
                f"• *Token IDs:* {ids_display}",
                f"• *Amounts:* {amounts_display}"
            ]
            sections.append(build_section("NFT Batch", token_rows))
            sections.append(build_section("Transfer", tx_rows))
        
        elif activity_type == "contract_interaction":
            contract_address = to_address if to_address != 'Unknown' else 'Contract Creation'
            function_name = tx_data.get('function_name', 'Unknown')
            value_eth = float(Web3.from_wei(int(value), 'ether')) if isinstance(value, (int, str)) and int(value) > 0 else 0
            contract_rows = [
                f"• *Contract:* `{format_address(contract_address)}`",
                f"• *Function:* `{function_name}`",
            ]
            if value_eth > 0:
                contract_rows.append(f"• *Value:* {value_eth:.6f} MON")
            sections.append(build_section("Interaction", contract_rows))
            sections.append(build_section("Transaction", tx_rows))
        
        elif activity_type == "contract_deployment":
            contract_address = tx_data.get('contract_address', 'Unknown')
            gas_used = tx_data.get('gas_used', 'N/A')
            deployment_rows = [
                f"• *New Contract:* `{format_address(contract_address)}`",
                f"• *Gas Used:* {gas_used}"
            ]
            sections.append(build_section("Deployment", deployment_rows))
            sections.append(build_section("Transaction", tx_rows))
        
        else:
            sections.append(build_section("Transaction", tx_rows))
        
        sections.append(f"⏱ *Updated:* {timestamp}")
        return "\n".join(sections).strip()
    except Exception as e:
        logger.error(f"Error formatting transaction: {e}")
        return f"New transaction: {tx_hash}"


def format_balance_change_message(wallet_address: str, old_balance: float, new_balance: float) -> str:
    """Format balance change message"""
    diff = new_balance - old_balance
    direction = "📈 *Balance Increased*" if diff > 0 else "📉 *Balance Decreased*"
    rows = [
        f"• *Previous:* {old_balance:.6f} MON",
        f"• *Current:* {new_balance:.6f} MON",
        f"• *Change:* {diff:+.6f} MON",
    ]
    message = [
        "💰 *Balance Alert*",
        direction,
        f"`{format_address(wallet_address)}`",
        build_section("Details", rows),
        f"⏱ *Updated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ]
    return "\n".join(message).strip()


async def check_balance_changes(wallet_address: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check for balance changes in native token"""
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        current_balance = w3.eth.get_balance(wallet_address)
        current_balance_eth = float(Web3.from_wei(current_balance, 'ether'))
        
        old_balance_str = db.get_balance(wallet_address)
        
        if old_balance_str is None:
            db.save_balance(wallet_address, str(current_balance), current_balance_eth, w3.eth.block_number)
            return
        
        old_balance = int(old_balance_str)
        old_balance_eth = float(Web3.from_wei(old_balance, 'ether'))
        
        if current_balance != old_balance:
            message = format_balance_change_message(wallet_address, old_balance_eth, current_balance_eth)
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            db.save_balance(wallet_address, str(current_balance), current_balance_eth, w3.eth.block_number)
            logger.info(f"Balance changed for wallet {wallet_address}")
            
    except Exception as e:
        logger.error(f"Error checking balance for {wallet_address}: {e}")


async def check_erc20_transfers(wallet_address: str, from_block: int, to_block: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check for ERC-20 token transfers"""
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        wallet_lower = wallet_address.lower()
        
        transfer_event_signature = w3.keccak(text="Transfer(address,address,uint256)").hex()
        
        logs = w3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': to_block,
            'topics': [transfer_event_signature]
        })
        
        for log in logs:
            try:
                from_addr = '0x' + log['topics'][1].hex()[26:]
                to_addr = '0x' + log['topics'][2].hex()[26:]
                amount = int(log['data'].hex(), 16)
                token_address = log['address']
                
                if from_addr.lower() == wallet_lower or to_addr.lower() == wallet_lower:
                    token_info = get_token_info(token_address)
                    
                    tx_data = {
                        'token_address': token_address,
                        'amount': amount,
                        'token_info': token_info,
                        'from': from_addr,
                        'to': to_addr,
                        'blockNumber': log['blockNumber']
                    }
                    
                    message = format_transaction_message(
                        log['transactionHash'].hex(),
                        tx_data,
                        wallet_address,
                        "erc20"
                    )
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    
                    # Save to database
                    db.save_transaction(
                        wallet_address,
                        log['transactionHash'].hex(),
                        "erc20",
                        {
                            'from': from_addr,
                            'to': to_addr,
                            'value': str(amount),
                            'token_address': token_address,
                            'token_symbol': token_info.get('symbol'),
                            'token_name': token_info.get('name'),
                            'block_number': log['blockNumber']
                        }
                    )
                    
                    logger.info(f"Found ERC-20 transfer for wallet {wallet_address}")
            except Exception as e:
                logger.error(f"Error processing ERC-20 log: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error checking ERC-20 transfers: {e}")


async def check_erc721_transfers(wallet_address: str, from_block: int, to_block: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check for ERC-721 NFT transfers"""
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        wallet_lower = wallet_address.lower()
        
        transfer_event_signature = w3.keccak(text="Transfer(address,address,uint256)").hex()
        
        logs = w3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': to_block,
            'topics': [transfer_event_signature]
        })
        
        for log in logs:
            try:
                from_addr = '0x' + log['topics'][1].hex()[26:]
                to_addr = '0x' + log['topics'][2].hex()[26:]
                token_id = int(log['topics'][3].hex(), 16)
                token_address = log['address']
                
                if from_addr.lower() == wallet_lower or to_addr.lower() == wallet_lower:
                    token_info = get_token_info(token_address)
                    
                    tx_data = {
                        'token_address': token_address,
                        'token_id': token_id,
                        'token_info': token_info,
                        'from': from_addr,
                        'to': to_addr,
                        'blockNumber': log['blockNumber']
                    }
                    
                    message = format_transaction_message(
                        log['transactionHash'].hex(),
                        tx_data,
                        wallet_address,
                        "erc721"
                    )
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    
                    db.save_transaction(
                        wallet_address,
                        log['transactionHash'].hex(),
                        "erc721",
                        {
                            'from': from_addr,
                            'to': to_addr,
                            'token_address': token_address,
                            'token_id': str(token_id),
                            'token_symbol': token_info.get('symbol'),
                            'token_name': token_info.get('name'),
                            'block_number': log['blockNumber']
                        }
                    )
                    
                    logger.info(f"Found ERC-721 transfer for wallet {wallet_address}")
            except Exception as e:
                logger.error(f"Error processing ERC-721 log: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error checking ERC-721 transfers: {e}")


async def check_erc1155_transfers(wallet_address: str, from_block: int, to_block: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check for ERC-1155 NFT transfers"""
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        wallet_lower = wallet_address.lower()
        
        transfer_single_signature = w3.keccak(text="TransferSingle(address,address,address,uint256,uint256)").hex()
        
        logs = w3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': to_block,
            'topics': [transfer_single_signature]
        })
        
        for log in logs:
            try:
                operator = '0x' + log['topics'][1].hex()[26:]
                from_addr = '0x' + log['topics'][2].hex()[26:]
                to_addr = '0x' + log['topics'][3].hex()[26:]
                
                data = log['data'].hex()
                token_id = int(data[2:66], 16)
                amount = int(data[66:130], 16)
                token_address = log['address']
                
                if from_addr.lower() == wallet_lower or to_addr.lower() == wallet_lower:
                    tx_data = {
                        'token_address': token_address,
                        'token_ids': [token_id],
                        'amounts': [amount],
                        'from': from_addr,
                        'to': to_addr,
                        'blockNumber': log['blockNumber']
                    }
                    
                    message = format_transaction_message(
                        log['transactionHash'].hex(),
                        tx_data,
                        wallet_address,
                        "erc1155"
                    )
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    
                    logger.info(f"Found ERC-1155 transfer for wallet {wallet_address}")
            except Exception as e:
                logger.error(f"Error processing ERC-1155 log: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error checking ERC-1155 transfers: {e}")


async def check_contract_interactions(wallet_address: str, from_block: int, to_block: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check for smart contract interactions"""
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        wallet_lower = wallet_address.lower()
        
        for block_num in range(from_block, to_block + 1):
            try:
                block = w3.eth.get_block(block_num, full_transactions=True)
                
                for tx in block.transactions:
                    tx_from = tx.get('from', '').lower() if tx.get('from') else ''
                    tx_to = tx.get('to', '').lower() if tx.get('to') else ''
                    input_data = tx.get('input', '0x')
                    
                    if tx_from == wallet_lower and input_data and input_data != '0x' and len(input_data) > 10:
                        function_name = get_function_name(input_data)
                        
                        if function_name not in ["transfer(address,uint256)", "transferFrom(address,address,uint256)"]:
                            tx_hash = tx['hash'].hex()
                            tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
                            
                            tx_data = {
                                'from': tx.get('from'),
                                'to': tx.get('to'),
                                'function_name': function_name,
                                'input': input_data,
                                'value': tx.get('value', 0),
                                'blockNumber': block_num,
                                'gas_used': tx_receipt.get('gasUsed')
                            }
                            
                            message = format_transaction_message(
                                tx_hash,
                                tx_data,
                                wallet_address,
                                "contract_interaction"
                            )
                            
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=message,
                                parse_mode='Markdown'
                            )
                            
                            db.save_transaction(
                                wallet_address,
                                tx_hash,
                                "contract_interaction",
                                {
                                    'from': tx.get('from'),
                                    'to': tx.get('to'),
                                    'function_name': function_name,
                                    'value': str(tx.get('value', 0)),
                                    'block_number': block_num,
                                    'gas_used': tx_receipt.get('gasUsed')
                                }
                            )
                            
                            logger.info(f"Found contract interaction for wallet {wallet_address}: {function_name}")
            except Exception as e:
                logger.error(f"Error processing block {block_num} for contract interactions: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error checking contract interactions: {e}")


async def check_internal_transactions(wallet_address: str, from_block: int, to_block: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check for internal transactions (contract deployments)"""
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        wallet_lower = wallet_address.lower()
        
        for block_num in range(from_block, to_block + 1):
            try:
                block = w3.eth.get_block(block_num, full_transactions=True)
                
                for tx in block.transactions:
                    tx_from = tx.get('from', '').lower() if tx.get('from') else ''
                    tx_to = tx.get('to')
                    
                    if tx_from == wallet_lower and not tx_to:
                        tx_hash = tx['hash'].hex()
                        tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
                        contract_address = tx_receipt.get('contractAddress')
                        
                        if contract_address:
                            tx_data = {
                                'contract_address': contract_address,
                                'blockNumber': block_num,
                                'gas_used': tx_receipt.get('gasUsed')
                            }
                            
                            message = format_transaction_message(
                                tx_hash,
                                tx_data,
                                wallet_address,
                                "contract_deployment"
                            )
                            
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=message,
                                parse_mode='Markdown'
                            )
                            
                            logger.info(f"Found contract deployment for wallet {wallet_address}")
            except Exception as e:
                logger.error(f"Error processing block {block_num} for internal transactions: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error checking internal transactions: {e}")


async def check_wallet_activity(wallet_address: str, user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check for all types of activities for a specific wallet"""
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        current_block = w3.eth.block_number
        
        last_block = db.get_last_processed_block(wallet_address)
        if last_block == 0:
            last_block = current_block - 100
        
        from_block = last_block + 1
        to_block = current_block
        
        if from_block > to_block:
            await check_balance_changes(wallet_address, chat_id, context)
            return
        
        logger.info(f"Checking blocks {from_block} to {to_block} for wallet {wallet_address}")
        
        # Check native token transactions
        for block_num in range(from_block, to_block + 1):
            try:
                block = w3.eth.get_block(block_num, full_transactions=True)
                
                for tx in block.transactions:
                    tx_from = tx.get('from', '').lower() if tx.get('from') else ''
                    tx_to = tx.get('to', '').lower() if tx.get('to') else ''
                    wallet_lower = wallet_address.lower()
                    value = tx.get('value', 0)
                    
                    if (tx_from == wallet_lower or tx_to == wallet_lower) and value > 0:
                        tx_hash = tx['hash'].hex()
                        tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
                        tx_data = dict(tx)
                        tx_data['blockNumber'] = block_num
                        tx_data['gas_used'] = tx_receipt.get('gasUsed')
                        
                        message = format_transaction_message(tx_hash, tx_data, wallet_address, "native")
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        
                        db.save_transaction(
                            wallet_address,
                            tx_hash,
                            "native",
                            {
                                'from': tx.get('from'),
                                'to': tx.get('to'),
                                'value': str(value),
                                'block_number': block_num,
                                'gas_used': tx_receipt.get('gasUsed')
                            }
                        )
                        
                        logger.info(f"Found native transaction {tx_hash} for wallet {wallet_address}")
            except Exception as e:
                logger.error(f"Error processing block {block_num}: {e}")
                continue
        
        # Check all other activity types
        await check_erc20_transfers(wallet_address, from_block, to_block, chat_id, context)
        await check_erc721_transfers(wallet_address, from_block, to_block, chat_id, context)
        await check_erc1155_transfers(wallet_address, from_block, to_block, chat_id, context)
        await check_contract_interactions(wallet_address, from_block, to_block, chat_id, context)
        await check_internal_transactions(wallet_address, from_block, to_block, chat_id, context)
        await check_balance_changes(wallet_address, chat_id, context)
        
        # Update last processed block
        db.update_last_processed_block(wallet_address, to_block)
        
    except Exception as e:
        logger.error(f"Error checking wallet {wallet_address}: {e}")


async def monitor_wallets(context: ContextTypes.DEFAULT_TYPE):
    """Check all tracked wallets once (JobQueue calls this periodically)."""
    try:
        wallets = db.get_all_tracked_wallets()
        for wallet_info in wallets:
            wallet_address = wallet_info['wallet_address']
            user_id = wallet_info['user_id']
            chat_id = wallet_info.get('chat_id')
            
            if chat_id:
                try:
                    await check_wallet_activity(wallet_address, user_id, chat_id, context)
                except Exception as e:
                    logger.error(f"Error monitoring wallet {wallet_address}: {e}")
    except Exception as e:
        logger.error(f"Error in monitor loop: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    db.add_user(user.id, chat_id, user.username, user.first_name, user.last_name)
    
    welcome_message = (
        "👋 *Hi! I'm MonTracker.*\n\n"
        "🔎 *What I watch*\n\n"
        "• MON transfers\n"
        "• ERC-20 token flows\n"
        "• ERC-721 / ERC-1155 NFTs\n"
        "• Contract interactions & deployments\n"
        "• Balance changes\n\n"
        "**Type /help to show all commands**\n\n"
        "💬 *Need help?* DM @velhust0x."
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addwallet command"""
    if not context.args:
        await update.message.reply_text("❌ Please provide a wallet address.\nExample: /addwallet 0x1234...")
        return
    
    wallet_address = context.args[0]
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        db.add_user(user.id, chat_id, user.username, user.first_name, user.last_name)
        
        current_block = w3.eth.block_number
        if db.add_wallet(wallet_address, user.id, current_block):
            # Initialize balance
            balance = w3.eth.get_balance(wallet_address)
            balance_eth = float(Web3.from_wei(balance, 'ether'))
            db.save_balance(wallet_address, str(balance), balance_eth, current_block)
            
            await update.message.reply_text(
                f"✅ *Tracking started*\n"
                f"📍 Wallet: `{wallet_address}`\n"
                f"🔔 I’ll alert you for MON, ERC-20, NFT, contract, and balance events.",
                parse_mode='Markdown'
            )
            logger.info(f"Added wallet {wallet_address} for user {user.id}")
        else:
            await update.message.reply_text("❌ Failed to add wallet. It may already be tracked.")
        
    except ValueError:
        await update.message.reply_text("❌ Invalid wallet address. Please check and try again.")
    except Exception as e:
        logger.error(f"Error adding wallet: {e}")
        await update.message.reply_text(f"❌ Error adding wallet: {str(e)}")


async def remove_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removewallet command"""
    if not context.args:
        await update.message.reply_text("❌ Please provide a wallet address.\nExample: /removewallet 0x1234...")
        return
    
    wallet_address = context.args[0]
    user = update.effective_user
    
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        
        if db.remove_wallet(wallet_address, user.id):
            await update.message.reply_text(
                f"🗑 *Tracking stopped*\n"
                f"📍 Wallet: `{wallet_address}`",
                parse_mode='Markdown'
            )
            logger.info(f"Removed wallet {wallet_address} for user {user.id}")
        else:
            await update.message.reply_text("❌ Wallet not found in your tracking list.")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid wallet address.")
    except Exception as e:
        logger.error(f"Error removing wallet: {e}")
        await update.message.reply_text(f"❌ Error removing wallet: {str(e)}")


async def list_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listwallets command"""
    user = update.effective_user
    wallets = db.get_user_wallets(user.id)
    
    if not wallets:
        await update.message.reply_text("📭 You haven't added any wallets to track yet.")
        return
    
    lines = ["📋 *Your wallets*"]
    for i, wallet in enumerate(wallets, 1):
        added_at = wallet['added_at'][:10] if wallet['added_at'] else 'N/A'
        lines.append(f"{i}. `{wallet['wallet_address']}` — added *{added_at}*")
    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    try:
        is_connected = w3.is_connected()
        current_block = w3.eth.block_number if is_connected else 0
        chain_id = w3.eth.chain_id if is_connected else 0
        all_wallets = db.get_all_tracked_wallets()
        
        status_message = (
            "📊 *Status*\n"
            f"• *Monad:* {'✅ up' if is_connected else '❌ down'}\n"
            f"• *Block:* #{current_block} (chain {chain_id})\n"
            f"• *Tracking:* {len(all_wallets)} wallets\n"
            f"• *Interval:* {CHECK_INTERVAL}s\n\n"
            "🛰 *Coverage:* MON, ERC-20, NFTs, contracts, balance."
        )
        await update.message.reply_text(status_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        await update.message.reply_text(f"❌ Error checking status: {str(e)}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = f"""
📖 *Commands*

• `/addwallet <address>` – Track a wallet
• `/removewallet <address>` – Stop tracking
• `/listwallets` – Show wallets
• `/status` – Bot health & stats
• `/help` – This list

💡 *Notes*
• Checks every {CHECK_INTERVAL}s
• Tracks from current block onward
• Requires valid 0x… address
"""

    await update.message.reply_text(help_text, parse_mode='Markdown')


def main():
    """Main function to start the bot"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return
    
    # Check Monad connection
    if not w3.is_connected():
        logger.warning(f"Warning: Could not connect to Monad RPC at {MONAD_RPC_URL}")
        logger.warning("Bot will start but may not function correctly.")
    else:
        logger.info(f"Connected to Monad mainnet. Current block: {w3.eth.block_number}")
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addwallet", add_wallet))
    application.add_handler(CommandHandler("removewallet", remove_wallet))
    application.add_handler(CommandHandler("listwallets", list_wallets))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help_command))
    
    # Start monitoring job
    job_queue = application.job_queue
    job_queue.run_repeating(
        monitor_wallets,
        interval=CHECK_INTERVAL,
        first=CHECK_INTERVAL
    )
    
    # Start bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
