from web3 import Web3
from loguru import logger
import time

class OrderParamsConverter:
    # Define limits and whitelist

    @staticmethod
    def dict_to_tuple(order_params):
        # Validate the order parameters
        # OrderParamsConverter.validate(order_params)

        offered_long_shares_params = (
            order_params["offeredLongSharesParams"]["floor"],
            order_params["offeredLongSharesParams"]["cap"],
            order_params["offeredLongSharesParams"]["index"],
            order_params["offeredLongSharesParams"]["targetStartTimestamp"],
            order_params["offeredLongSharesParams"]["targetEndTimestamp"],
            order_params["offeredLongSharesParams"]["payoutToken"],
        )

        requested_long_shares_params = (
            order_params["requestedLongSharesParams"]["floor"],
            order_params["requestedLongSharesParams"]["cap"],
            order_params["requestedLongSharesParams"]["index"],
            order_params["requestedLongSharesParams"]["targetStartTimestamp"],
            order_params["requestedLongSharesParams"]["targetEndTimestamp"],
            order_params["requestedLongSharesParams"]["payoutToken"],
        )

        return (
            order_params["maker"],
            order_params["taker"],
            order_params["expiry"],
            order_params["offeredUpfrontToken"],
            order_params["offeredUpfrontAmount"],
            offered_long_shares_params,
            order_params["offeredLongShares"],
            order_params["requestedUpfrontToken"],
            order_params["requestedUpfrontAmount"],
            requested_long_shares_params,
            order_params["requestedLongShares"],
        )

class ContractCalls:
    def __init__(self, web3: Web3, contract, account_address: str, private_key: str):
        self.web3 = web3
        self.contract = contract
        self.account_address = account_address
        self.private_key = private_key

    def fill_order(self, order_data: dict) -> str:
        try:
            signature = bytes.fromhex(order_data["signature"][2:])
            fraction = Web3.to_wei(order_data.get("fraction", 1), "ether")
            txn = self.contract.functions.fillOrder(
                OrderParamsConverter.dict_to_tuple(order_data), signature, fraction
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