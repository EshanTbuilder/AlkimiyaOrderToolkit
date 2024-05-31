from datetime import datetime
from decimal import Decimal

BTCTXFEE_DECIMALS = 3

def date_to_block_timestamp(date):
    return int(date.timestamp())

def size_kb_to_shares(size_kb: Decimal, target_start_timestamp: datetime, target_end_timestamp: datetime) -> Decimal:

    start_timestamp = date_to_block_timestamp(target_start_timestamp)
    end_timestamp = date_to_block_timestamp(target_end_timestamp)
    block_duration = 600 
    num_blocks = round((end_timestamp - start_timestamp) / block_duration)

    size_bytes = size_kb * 1000
    bytes_per_block = size_bytes / num_blocks
    silica_wei_per_block = round(bytes_per_block * 10 ** BTCTXFEE_DECIMALS)
    return silica_wei_per_block

def shares_to_size_kb(shares: Decimal, target_start_timestamp: datetime, target_end_timestamp: datetime) -> Decimal:
    # Calculate the number of blocks between the start and end timestamps
    start_timestamp = date_to_block_timestamp(target_start_timestamp)
    end_timestamp = date_to_block_timestamp(target_end_timestamp)
    block_duration = 600  # Bitcoin block duration is approximately 10 minutes (600 seconds)
    num_blocks = round((end_timestamp - start_timestamp) / block_duration)

    silica_wei_per_block = shares
    bytes_per_block = silica_wei_per_block / (10 ** BTCTXFEE_DECIMALS)
    size_bytes = bytes_per_block * num_blocks
    size_kb = size_bytes / 1000

    return size_kb
