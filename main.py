import asyncio
import datetime
from pools import PoolData
from orders import Order
from graphql_calls import place_order
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
from utils import shares_to_size_kb, size_kb_to_shares, date_to_block_timestamp
from contract_calls import ContractCalls
from config import Config
from loguru import logger
from web3.middleware import geth_poa_middleware
from web3 import Web3
import aiohttp
from eth_account.messages import encode_defunct
from eth_account import Account
import json

ACCOUNT = Config.get_str("ACCOUNT", "0x9B2BF12f94412546829dE1aE34B36EB76FdCD0a4")
PRIVATE_KEY = Config.get_str("PRIVATE_KEY")
CONTRACT_ADDRESS = Config.get_str("CONTRACT_ADDRESS", "0x71486c325a1dfd990a3a21d8debe82d1d4ed3c88")
WEB3_HTTP_URL = Config.get_str("WEB3_HTTP_URL")
CHAIN_ID = 11155111

zero_address = "0x0000000000000000000000000000000000000000"
zero_pool = "0x0000000000000000000000000000000000000000"

def is_supported_chain_id(chain_id):
    return chain_id in {11155111, 1}

def make_order_domain(chain_id):
    return {
        "name": "SilicaPools",
        "version": "1",
        "chainId": chain_id,
        "verifyingContract": CONTRACT_ADDRESS
    }

order_types = {
    "PoolParams": [
        {"name": "floor", "type": "uint128"},
        {"name": "cap", "type": "uint128"},
        {"name": "index", "type": "address"},
        {"name": "targetStartTimestamp", "type": "uint48"},
        {"name": "targetEndTimestamp", "type": "uint48"},
        {"name": "payoutToken", "type": "address"},
    ],
    "SilicaOrder": [
        {"name": "maker", "type": "address"},
        {"name": "taker", "type": "address"},
        {"name": "expiry", "type": "uint48"},
        {"name": "offeredUpfrontToken", "type": "address"},
        {"name": "offeredUpfrontAmount", "type": "uint128"},
        {"name": "offeredLongShares", "type": "uint128"},
        {"name": "offeredLongSharesParams", "type": "PoolParams"},
        {"name": "requestedUpfrontToken", "type": "address"},
        {"name": "requestedUpfrontAmount", "type": "uint128"},
        {"name": "requestedLongShares", "type": "uint128"},
        {"name": "requestedLongSharesParams", "type": "PoolParams"},
    ]
}

order_primary_type = "SilicaOrder"

def make_order_message(pool: PoolData, order):
    offered_long_shares = Decimal(order["offeredLongShares"])
    requested_long_shares = Decimal(order["requestedLongShares"])
    
    if offered_long_shares != 0 and requested_long_shares != 0:
        raise ValueError("Error[orderMessage]: Pool-for-pool trades are currently not supported.")
    
    pool_message = {
        "floor": Decimal(pool.floor),
        "cap": Decimal(pool.cap),
        "index": pool.index,
        "targetStartTimestamp": pool.target_start_timestamp.timestamp(),
        "targetEndTimestamp": pool.target_end_timestamp.timestamp(),
        "payoutToken": pool.payout_token
    }
    
    order_message = {
        "maker": order["maker"],
        "taker": zero_address,
        "expiry": int(order["expiry"]),
        "offeredUpfrontToken": order.get("offeredUpfrontToken", zero_address),
        "offeredUpfrontAmount": Decimal(order["offeredUpfrontAmount"]),
        "offeredLongShares": offered_long_shares,
        "offeredLongSharesParams": zero_pool if offered_long_shares == 0 else pool_message,
        "requestedUpfrontToken": order.get("requestedUpfrontToken", zero_address),
        "requestedUpfrontAmount": Decimal(order["requestedUpfrontAmount"]),
        "requestedLongShares": requested_long_shares,
        "requestedLongSharesParams": zero_pool if requested_long_shares == 0 else pool_message
    }
    
    return order_message

def sign_order_payload(pool, order):
    if not is_supported_chain_id(order["chainId"]):
        raise ValueError(f"Chain ID {order['chainId']} is not supported.")
    
    payload = {
        "domain": make_order_domain(order["chainId"]),
        "types": order_types,
        "primaryType": order_primary_type,
        "message": make_order_message(pool, order)
    }
    
    return payload

def hash_order(pool, order):
    payload = sign_order_payload(pool, order)
    payload_data = json.dumps(payload, default=str).encode('utf-8')
    hash = Web3.solidity_keccak(
        ['bytes'],
        [payload_data]
    ).hex()
    return hash

def generate_signature(order_hash, private_key):
    logger.debug(order_hash)
    message = encode_defunct(text=order_hash)
    
    logger.debug(f"message: {message}")
    signed_message = Account.sign_message(message, private_key=private_key)
    return signed_message.signature.hex()


async def create_order(
    pool_data: PoolData, 
    price: Decimal, 
    size: Decimal, 
    direction: str, 
    expiry: datetime
) -> Order:
    
    # Generate a unique order ID and hash (you may want to replace this with a real hashing function)
    order_id = str(uuid.uuid4())
    order_hash = str(uuid.uuid4())  # Placeholder for actual hash generation
    # Calculate the requested and offered amounts based on direction
    requested_upfront_token=None
    offered_upfront_token=None
    if direction == "LONG":
        requested_upfront_token=pool_data.payout_token,
    elif direction == "SHORT":
        offered_upfront_token=pool_data.payout_token,
    else:
        raise ValueError("Direction must be either 'LONG' or 'SHORT'")
    
    # Create the Order object
    new_order = Order(
        id=order_id,
        order_hash=order_hash,
        expiry=expiry,
        pool_id=pool_data.id,
        maker=ACCOUNT,  # Replace with actual maker address
        direction=direction,
        signature="0xSignatureHere",  # Replace with actual signature
        requested_long_shares=None,
        offered_long_shares=None,
        offered_upfront_token=offered_upfront_token,
        requested_upfront_token=requested_upfront_token,
        requested_upfront_amount=None,
        offered_upfront_amount=None,
        fraction_filled=Decimal("0")
    )
    new_order.from_price_and_size(price, size, pool_data)
    new_order.signature = generate_signature(hash_order(pool_data, generate_order_payload_for_hash(new_order)), PRIVATE_KEY)
    
    return new_order
def generate_order_payload_for_hash(order: Order) -> Dict[str, Any]:
    return {
        "maker": order.maker,
        "expiry": order.expiry.timestamp(),
        "offeredUpfrontToken": order.offered_upfront_token or "0x0000000000000000000000000000000000000000",
        "offeredUpfrontAmount": str(int(order.offered_upfront_amount)) if order.offered_upfront_amount else "0",
        "offeredLongShares": str(int(order.offered_long_shares)) if order.offered_long_shares else "0",
        "requestedUpfrontToken": order.requested_upfront_token or "0x0000000000000000000000000000000000000000",
        "requestedUpfrontAmount": str(int(order.requested_upfront_amount)) if order.requested_upfront_amount else "0",
        "requestedLongShares": str(int(order.requested_long_shares)) if order.requested_long_shares else "0",
        "signature": order.signature,
        "chainId": 11155111,  # Adjust as needed
        "direction": order.direction,
        "poolId": order.pool_id,
    }
def generate_order_payload(order: Order) -> Dict[str, Any]:
    return {
        "maker": order.maker,
        "expiry": order.expiry.isoformat(),
        "offeredUpfrontToken": order.offered_upfront_token or "0x0000000000000000000000000000000000000000",
        "offeredUpfrontAmount": str(int(order.offered_upfront_amount)) if order.offered_upfront_amount else "0",
        "offeredLongShares": str(int(order.offered_long_shares)) if order.offered_long_shares else "0",
        "requestedUpfrontToken": order.requested_upfront_token or "0x0000000000000000000000000000000000000000",
        "requestedUpfrontAmount": str(int(order.requested_upfront_amount)) if order.requested_upfront_amount else "0",
        "requestedLongShares": str(int(order.requested_long_shares)) if order.requested_long_shares else "0",
        "signature": order.signature,
        "chainId": 11155111,  # Adjust as needed
        "direction": order.direction,
        "poolId": order.pool_id,
    }
async def main():
    
    web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_URL))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    contract_abi = None
    with open(f"contracts/{CONTRACT_ADDRESS}.abi.json") as contract_file:
        contract_abi = contract_file.read()
    contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)
    
    contract_call = ContractCalls(web3, contract, ACCOUNT, PRIVATE_KEY)
    pool_data = PoolData.from_json(
        {
            "id": "ac410f4e-1a2e-4c43-b44e-c20352781815",
            "poolHash": "0x960ef4c70370e29f42ad5186381ace4b57e2c325f9a219a97ab2f2d162cb81fb",
            "index": "0xBDB06E1FBfAb742F0f5e72a85E57418437D505e9",
            "indexName": "BTC_TX_FEE",
            "cap": "23184",
            "floor": "0",
            "payoutToken": "0x23aC6531349546f0909A9Cd06D3fC7A0be67E9b6",
            "targetEndTimestamp": "2024-06-04T03:00:00.000Z",
            "targetStartTimestamp": "2024-05-28T03:00:00.000Z",
            "totalUpfrontPayment": {"amount": "67381000"},
            "state": {
                "actualEndTimestamp": None,
                "balanceChangePerShare": None,
                "collateralMinted": "260751003",
                "sharesMinted": "11247024",
                "totalMinted": "11247024",
            },
        }
    )
    
    order = await create_order(pool_data, Decimal('5000'), Decimal('1'), "LONG", datetime.now() + timedelta(days=1))
    logger.info(order)
    
    async with aiohttp.ClientSession() as session:
        logger.debug(await place_order(session, generate_order_payload(order)))
    
    


if __name__ == "__main__":
    asyncio.run(main())