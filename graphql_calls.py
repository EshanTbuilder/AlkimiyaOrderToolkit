import ssl
from loguru import logger

URL = "https://api.alkimiya.io/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
}
# GraphQL Queries
QUERIES = {
    "pools": """query Pools { pools { id poolHash index indexName cap floor payoutToken targetEndTimestamp targetStartTimestamp totalUpfrontPayment { amount } state { actualEndTimestamp balanceChangePerShare collateralMinted sharesMinted totalMinted } }}""",
    "orders": """query Orders($filter: FilterOrdersInput) { orders(filter: $filter) { state { fractionFilled } id orderHash expiry poolId maker direction signature requestedLongShares offeredLongShares offeredUpfrontToken requestedUpfrontToken requestedUpfrontAmount offeredUpfrontAmount }}""",
    "positions": """query Positions($filter: FilterTokenBalancesInput) { tokenBalances(filter: $filter) { poolHash direction balance }}""",
    "my_orders": """query GetMyOrders($filter: FilterOrdersInput) { orders(filter: $filter) { id poolId state { fractionFilled } ...OrderParams } } fragment OrderParams on Order { id orderHash expiry poolId maker direction signature requestedLongShares offeredLongShares offeredUpfrontToken requestedUpfrontToken requestedUpfrontAmount offeredUpfrontAmount }""",
    "trade_history": """query GetTradeHistory($poolHash: EthereumHash!) { tradesByPoolHash(poolHash: $poolHash) { id blockTimestamp filledFraction order { state { fractionFilled } id orderHash expiry poolId maker direction signature requestedLongShares offeredLongShares offeredUpfrontToken requestedUpfrontToken requestedUpfrontAmount offeredUpfrontAmount } }}""",
}


async def place_order(session, variables):
    headers = {
      "Content-Type": "application/json",
      "Accept": "*/*",
      "Accept-Encoding": "gzip, deflate, br, zstd",
      "Accept-Language": "en-US,en;q=0.9",
      "Dnt": "1",
      "Origin": "https://bazaar.alkimiya.io",
      "Referer": "https://bazaar.alkimiya.io/",
      "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
      "Sec-Ch-Ua-Mobile": "?0",
      "Sec-Ch-Ua-Platform": '"macOS"',
      "Sec-Fetch-Dest": "empty",
      "Sec-Fetch-Mode": "cors",
      "Sec-Fetch-Site": "same-site",
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
  }

    mutation = """
    mutation CreateOrder($input: CreateOrderInput!) {
      createOrder(createOrderInput: $input) {
        id
      }
    }
    """
    payload = {
        "query": mutation,
        "variables": {"input": variables}
    }
    
    ssl_context = ssl.create_default_context()
    async with session.post(URL, json=payload, headers=headers, ssl=ssl_context) as response:
        if response.status == 200:
            return await response.json()
        else:
            logger.error(
                f"Query failed to run with status code {response.status}. Response: {await response.text()}"
            )
            return None