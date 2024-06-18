from web3 import Web3
from loguru import logger
import time
import json
from datetime import datetime
from eth_account.messages import encode_defunct
from eth_account import Account

class OrderParamsConverter:
    # Define limits and whitelist

    @staticmethod
    def dict_to_tuple(order_params, pool_data):
        shares_params_empty = (
            0, 0, "0x0000000000000000000000000000000000000000", 0, 0, "0x0000000000000000000000000000000000000000"
        )
        # Create hardcoded tuples for offered_long_shares_params and requested_long_shares_params
        offered_long_shares_params = (
            pool_data.floor,  # floor
            pool_data.cap,  # cap
            pool_data.index,  # index
            int(pool_data.target_start_timestamp.timestamp()),  # targetStartTimestamp
            int(pool_data.target_end_timestamp.timestamp()),  # targetEndTimestamp
            pool_data.payout_token  # payoutToken
        )

        requested_long_shares_params = (
            pool_data.floor,  # floor
            pool_data.cap,  # cap
            pool_data.index,  # index
            int(pool_data.target_start_timestamp.timestamp()),  # targetStartTimestamp
            int(pool_data.target_end_timestamp.timestamp()),  # targetEndTimestamp
            pool_data.payout_token  # payoutToken
        )

        if order_params["direction"] == "SHORT":
            return (
                order_params["maker"],
                order_params["taker"],
                int(datetime.strptime(order_params["expiry"], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()),
                order_params.get("offered_upfront_token") or "0x0000000000000000000000000000000000000000",  # Default to zero address if None
                int(order_params.get("offered_upfront_amount", 0)),  # Default to 0 if None
                offered_long_shares_params,
                int(order_params["requested_long_shares"], 0) or 0,
                order_params.get("requested_upfront_token") or "0x0000000000000000000000000000000000000000",  # Default to zero address if None
                int(order_params.get("requested_upfront_amount", 0) or 0) or 0,  # Default to 0 if None
                shares_params_empty,
                0,  # Set requested_long_shares to 0 for SHORT direction
            )
        else:
            return None


class ContractCalls:
    def __init__(self, web3: Web3, contract, account_address: str, private_key: str):
        self.web3 = web3
        self.contract = contract
        self.account_address = account_address
        self.private_key = private_key

    def fill_order(self, order_data: dict, pool_data: dict) -> str:
        try:
            fraction = Web3.to_wei(order_data.get("fraction", 1), "ether")  # Ensure fraction is uint256
            logger.info(f"fraction: {fraction}")
            logger.info(json.dumps(order_data))
            
            # import ipdb; ipdb.set_trace()
            order_tuple = OrderParamsConverter.dict_to_tuple(order_data, pool_data)
            message = encode_defunct(text=str(order_tuple))
            account = Account.from_key(self.private_key)

            signed_message = account.sign_message(message)
            signature = signed_message.signature.hex()
            signature = bytes.fromhex(order_data["signature"][2:]) # this did not work
            logger.info(f"signature: {signature}")
            logger.info(order_tuple)
            txn = self.contract.functions.fillOrder(
                order_tuple, signature, fraction
            ).build_transaction({
                "chainId": self.web3.eth.chain_id,
                "gas": 50000,
                "gasPrice": self.web3.to_wei("50", "gwei"),
                "nonce": self.web3.eth.get_transaction_count(self.account_address),
            })
            signed_txn = self.web3.eth.account.sign_transaction(txn, private_key=self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            logger.info(f"Fill Order TX Hash: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Exception during order fill: {e}")
            raise e

    def cancel_order(self, order_data: dict) -> str:
        try:
            txn = self.contract.functions.cancelOrders(
                [order_data]
            ).build_transaction({
                "chainId": self.web3.eth.chain_id,
                "gas": 50000,
                "gasPrice": self.web3.to_wei("50", "gwei"),
                "nonce": self.web3.eth.get_transaction_count(self.account_address),
            })
            signed_txn = self.web3.eth.account.sign_transaction(txn, private_key=self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            logger.info(f"Cancel Order TX Hash: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Exception during order cancel: {e}")
            raise e