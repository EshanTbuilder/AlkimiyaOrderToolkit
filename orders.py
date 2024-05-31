from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from loguru import logger

from pools import PoolData
from utils import shares_to_size_kb, size_kb_to_shares


class Order:
    def __init__(
        self,
        id: str,
        order_hash: str,
        expiry: datetime,
        pool_id: str,
        maker: str,
        direction: str,
        signature: str,
        requested_long_shares: Optional[Decimal],
        offered_long_shares: Optional[Decimal],
        offered_upfront_token: Optional[str],
        requested_upfront_token: Optional[str],
        requested_upfront_amount: Optional[Decimal],
        offered_upfront_amount: Optional[Decimal],
        fraction_filled: Decimal,
    ):
        self.id = id
        self.order_hash = order_hash
        self.expiry = expiry
        self.pool_id = pool_id
        self.maker = maker
        self.direction = direction
        self.signature = signature
        self.requested_long_shares = requested_long_shares
        self.offered_long_shares = offered_long_shares
        self.offered_upfront_token = offered_upfront_token
        self.requested_upfront_token = requested_upfront_token
        self.requested_upfront_amount = requested_upfront_amount
        self.offered_upfront_amount = offered_upfront_amount
        self.fraction_filled = fraction_filled

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Order":
        try:
            id = data["id"]
            order_hash = data["orderHash"]
            expiry = datetime.fromisoformat(data["expiry"].replace("Z", "+00:00"))
            pool_id = data["poolId"]
            maker = data["maker"]
            direction = data["direction"]
            signature = data["signature"]

            requested_long_shares = (
                Decimal(data["requestedLongShares"])
                if data["requestedLongShares"]
                else None
            )
            offered_long_shares = (
                Decimal(data["offeredLongShares"])
                if data["offeredLongShares"]
                else None
            )
            offered_upfront_token = data["offeredUpfrontToken"]
            requested_upfront_token = data["requestedUpfrontToken"]
            requested_upfront_amount = (
                Decimal(data["requestedUpfrontAmount"])
                if data["requestedUpfrontAmount"]
                else None
            )
            offered_upfront_amount = (
                Decimal(data["offeredUpfrontAmount"])
                if data["offeredUpfrontAmount"]
                else None
            )
            fraction_filled = Decimal(data["state"]["fractionFilled"])
        except KeyError as ke:
            logger.error(data)
            logger.error(ke)
            raise ke

        return cls(
            id,
            order_hash,
            expiry,
            pool_id,
            maker,
            direction,
            signature,
            requested_long_shares,
            offered_long_shares,
            offered_upfront_token,
            requested_upfront_token,
            requested_upfront_amount,
            offered_upfront_amount,
            fraction_filled,
        )

    def to_dict(self, pool_data) -> Dict[str, Any]:
        target_start_timestamp = int(
            datetime.fromisoformat(
                pool_data.target_start_timestamp.isoformat().replace("Z", "+00:00")
            ).timestamp()
        )
        target_end_timestamp = int(
            datetime.fromisoformat(
                pool_data.target_end_timestamp.isoformat().replace("Z", "+00:00")
            ).timestamp()
        )

        return {
            "maker": self.maker,
            "taker": "0x0000000000000000000000000000000000000000",
            "expiry": int(self.expiry.timestamp()),
            "offeredUpfrontToken": self.offered_upfront_token,
            "offeredUpfrontAmount": (
                int(self.offered_upfront_amount) if self.offered_upfront_amount else 0
            ),
            "offeredLongShares": (
                int(self.offered_long_shares) if self.offered_long_shares else 0
            ),
            "offeredLongSharesParams": {
                "floor": pool_data.floor,
                "cap": pool_data.cap,
                "index": pool_data.index,
                "targetStartTimestamp": target_start_timestamp,
                "targetEndTimestamp": target_end_timestamp,
                "payoutToken": pool_data.payout_token,
            },
            "requestedUpfrontToken": self.requested_upfront_token
            or "0x0000000000000000000000000000000000000000",
            "requestedUpfrontAmount": (
                int(self.requested_upfront_amount)
                if self.requested_upfront_amount
                else 0
            ),
            "requestedLongShares": (
                int(self.requested_long_shares) if self.requested_long_shares else 0
            ),
            "requestedLongSharesParams": {
                "floor": 0,
                "cap": 0,
                "index": "0x0000000000000000000000000000000000000000",
                "targetStartTimestamp": 0,
                "targetEndTimestamp": 0,
                "payoutToken": "0x0000000000000000000000000000000000000000",
            },
            "signature": self.signature,
        }

    def __repr__(self) -> str:
        return (
            f"Order(id={self.id}, order_hash={self.order_hash}, expiry={self.expiry}, pool_id={self.pool_id}, "
            f"maker={self.maker}, direction={self.direction}, signature={self.signature}, "
            f"requested_long_shares={self.requested_long_shares}, offered_long_shares={self.offered_long_shares}, "
            f"offered_upfront_token={self.offered_upfront_token}, requested_upfront_token={self.requested_upfront_token}, "
            f"requested_upfront_amount={self.requested_upfront_amount}, offered_upfront_amount={self.offered_upfront_amount}, "
            f"fraction_filled={self.fraction_filled})"
        )

    def to_price_and_size(self, pool_data: PoolData) -> Tuple[Decimal, Decimal]:
        """
        price will be defined as sat/kb
        size will be defined as kb
        """
        price = None
        size = None

        if self.direction == "LONG":
            size = Decimal(str(self.requested_long_shares))
            price = Decimal(str(self.offered_upfront_amount))

        elif self.direction == "SHORT":
            size = Decimal(str(self.offered_long_shares))
            price = Decimal(str(self.requested_upfront_amount))

        start = pool_data.target_start_timestamp
        end = pool_data.target_end_timestamp
        # convert size from shares to kb
        size_kb = shares_to_size_kb(size, start, end)
        # convert price to sat / kb
        price_satPkb = price / size_kb

        return price_satPkb, size_kb

    def from_price_and_size(self, price, size, pool_data):
        start = pool_data.target_start_timestamp
        end = pool_data.target_end_timestamp

        size_shares = size_kb_to_shares(size, start, end)
        up_front_amount = price * size

        if self.direction == "LONG":
            self.requested_long_shares = size_shares
            self.offered_upfront_amount = up_front_amount

        elif self.direction == "SHORT":
            self.offered_long_shares = size_shares
            self.requested_upfront_amount = up_front_amount
