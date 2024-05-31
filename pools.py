from datetime import datetime
from typing import Optional, Dict, Any

class PoolData:
    def __init__(
        self,
        id: str,
        pool_hash: str,
        index: str,
        index_name: str,
        cap: int,
        floor: int,
        payout_token: str,
        target_end_timestamp: datetime,
        target_start_timestamp: datetime,
        total_upfront_payment: int,
        actual_end_timestamp: Optional[datetime],
        balance_change_per_share: Optional[int],
        collateral_minted: int,
        shares_minted: int,
        total_minted: int,
    ):
        self.id = id
        self.pool_hash = pool_hash
        self.index = index
        self.index_name = index_name
        self.cap = cap
        self.floor = floor
        self.payout_token = payout_token
        self.target_end_timestamp = target_end_timestamp
        self.target_start_timestamp = target_start_timestamp
        self.total_upfront_payment = total_upfront_payment
        self.actual_end_timestamp = actual_end_timestamp
        self.balance_change_per_share = balance_change_per_share
        self.collateral_minted = collateral_minted
        self.shares_minted = shares_minted
        self.total_minted = total_minted

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "PoolData":
        id = data["id"]
        pool_hash = data["poolHash"]
        index = data["index"]
        index_name = data["indexName"]
        cap = int(data["cap"])
        floor = int(data["floor"])
        payout_token = data["payoutToken"]
        target_end_timestamp = datetime.fromisoformat(
            data["targetEndTimestamp"].replace("Z", "+00:00")
        )
        target_start_timestamp = datetime.fromisoformat(
            data["targetStartTimestamp"].replace("Z", "+00:00")
        )
        total_upfront_payment = int(data["totalUpfrontPayment"]["amount"])

        state = data["state"]
        actual_end_timestamp = (
            datetime.fromisoformat(state["actualEndTimestamp"].replace("Z", "+00:00"))
            if state["actualEndTimestamp"]
            else None
        )
        balance_change_per_share = (
            int(state["balanceChangePerShare"])
            if state["balanceChangePerShare"]
            else None
        )
        collateral_minted = int(state["collateralMinted"])
        shares_minted = int(state["sharesMinted"])
        total_minted = int(state["totalMinted"])

        return cls(
            id,
            pool_hash,
            index,
            index_name,
            cap,
            floor,
            payout_token,
            target_end_timestamp,
            target_start_timestamp,
            total_upfront_payment,
            actual_end_timestamp,
            balance_change_per_share,
            collateral_minted,
            shares_minted,
            total_minted,
        )

    def __repr__(self) -> str:
        return (
            f"PoolData(id={self.id}, pool_hash={self.pool_hash}, index={self.index}, index_name={self.index_name}, "
            f"cap={self.cap}, floor={self.floor}, payout_token={self.payout_token}, "
            f"target_end_timestamp={self.target_end_timestamp}, target_start_timestamp={self.target_start_timestamp}, "
            f"total_upfront_payment={self.total_upfront_payment}, actual_end_timestamp={self.actual_end_timestamp}, "
            f"balance_change_per_share={self.balance_change_per_share}, collateral_minted={self.collateral_minted}, "
            f"shares_minted={self.shares_minted}, total_minted={self.total_minted})"
        )