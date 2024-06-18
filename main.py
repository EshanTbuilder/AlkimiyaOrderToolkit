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

ACCOUNT = Config.get_str("ACCOUNT", "0x985aA7045Fd77F5CCE7FE288264E620FB29fbb03")
PRIVATE_KEY = Config.get_str("PRIVATE_KEY")
CONTRACT_ADDRESS = Config.get_str("CONTRACT_ADDRESS", "0x71486c325a1dfd990a3a21d8debe82d1d4ed3c88")
WEB3_HTTP_URL = Config.get_str("WEB3_HTTP_URL", "https://eth-sepolia.g.alchemy.com/v2/9yB_MqlkC6S3wwNuUsZBMJxA7h4Yuy2p")
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
            "id": "b8c2d443-ef62-4c03-afbf-d0d4e77c8852",
            "poolHash": "0x2032def583038eb920f09eb011e4d0e403c4615aef9a2f3af651627808e14888",
            "index": "0xBDB06E1FBfAb742F0f5e72a85E57418437D505e9",
            "indexName": "BTC_TX_FEE",
            "cap": "504000",
            "floor": "0",
            "payoutToken": "0x23aC6531349546f0909A9Cd06D3fC7A0be67E9b6",
            "targetEndTimestamp": "2024-05-06T03:00:00.000Z",
            "targetStartTimestamp": "2024-04-29T03:00:00.000Z",
            "totalUpfrontPayment": {
                "amount": "10067400000"
            },
            "state": {
                "actualEndTimestamp": "2024-05-06T03:00:12.000Z",
                "balanceChangePerShare": "28816",
                "collateralMinted": "16534919350",
                "sharesMinted": "32807533",
                "totalMinted": "32807533"
            }
        },
    )
    
    #order = await create_order(pool_data, Decimal('5000'), Decimal('1'), "LONG", datetime.now() + timedelta(days=1))
    order = Order.from_json({
        "state": {
            "fractionFilled": "0"
        },
        "id": "548ed538-792c-4c08-af61-eb9fa6239091",
        "orderHash": "0x33fa6e05b5de97a48ecef49c04e2ca609a81c5c6b90abc6a81b68525465077ed",
        "expiry": "2024-06-15T12:19:43.663Z",
        "poolId": "b928cbe6-569b-4209-a421-53c624a9870a",
        "maker": "0xd01C9047f8918D1296C87024219a728Ec5Dd515b",
        "direction": "SHORT",
        "signature": "0xee565ea04f06fab92289e9f71a35a211ac8ce48cea6d592d7b1c1e76d599eadc35e0b3358810bba690ba9debe9d148e21e1c825ba877a76451ac6e2ad04c29d41b",
        "requestedLongShares": None,
        "offeredLongShares": "198413",
        "offeredUpfrontToken": None,
        "requestedUpfrontToken": "0x23aC6531349546f0909A9Cd06D3fC7A0be67E9b6",
        "requestedUpfrontAmount": "15200000",
        "offeredUpfrontAmount": None
    })
    
    
    # async with aiohttp.ClientSession() as session:
    #     logger.debug(await place_order(session, generate_order_payload(order)))
    
    # @staticmethod


    # Example dictionary
    order_params = {
        "id": "548ed538-792c-4c08-af61-eb9fa6239091",
        "order_hash": "0x33fa6e05b5de97a48ecef49c04e2ca609a81c5c6b90abc6a81b68525465077ed",
        "expiry": "2024-06-15T12:19:43.663000+00:00",
        "pool_id": "b928cbe6-569b-4209-a421-53c624a9870a",
        "maker": "0xd01C9047f8918D1296C87024219a728Ec5Dd515b",
        "taker": ACCOUNT,
        "direction": "SHORT",
        "signature": "0xee565ea04f06fab92289e9f71a35a211ac8ce48cea6d592d7b1c1e76d599eadc35e0b3358810bba690ba9debe9d148e21e1c825ba877a76451ac6e2ad04c29d41b",
        "requested_long_shares": None,
        "offered_long_shares": "198413",
        "offered_upfront_token": None,
        "requested_upfront_token": "0x23aC6531349546f0909A9Cd06D3fC7A0be67E9b6",
        "requested_upfront_amount": "15200000",
        "offered_upfront_amount": None,
        "fraction_filled": "0"
    }
    order_params = {
        "state": {
            "fractionFilled": "0"
        },
        "id": "1abb4265-cb5f-49ee-b7fe-f2e0cf496abd",
        "orderHash": "0x9cfb5c18bb791449d1551564c040356486267ff1b6790f11c77e4a183211a8e7",
        "expiry": "2024-06-19T03:51:13.584Z",
        "poolId": "fa6305cd-971d-47bf-a88f-df0d130b83ae",
        "maker": "0x632D6c5b1d1dc50a039B2AC5c86bf2014bfD2914",
        "taker": ACCOUNT,
        "direction": "SHORT",
        "signature": "0xa878e01b37f6070214f9132641a531e9dd4eb9b2119139486724108f061d68067d5c482443dde0286d36eb733cdefdf20539a7af28db52ede9d2919f006b5dca1b",
        "requested_long_shares": "9921",
        "offered_long_shares": None,
        "offered_upfront_token": "0x23aC6531349546f0909A9Cd06D3fC7A0be67E9b6",
        "requested_upfront_token": None,
        "requested_upfront_amount": None,
        "offered_upfront_amount": "190000"
    }

    # Test the function
    logger.info(order_params)
    logger.info(ContractCalls(web3, contract, ACCOUNT, PRIVATE_KEY).fill_order(order_params, pool_data))

    
    


if __name__ == "__main__":
    asyncio.run(main())