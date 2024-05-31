# Alkimiya Order Toolkit

This repository provides tools and utilities for interacting with the Alkimiya API and Ethereum blockchain to create, sign, and manage orders. It includes configuration management, GraphQL calls, and smart contract interactions.

## Features

- Configuration management using environment variables.
- GraphQL calls for fetching pool and order data.
- Smart contract interactions for filling and canceling orders.
- Utility functions for date conversion and size/share calculations.
- Order creation, signing, and payload generation.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- `pip` (Python package installer)
- Environment variables for configuration

### Installation

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/alkimiya-order-toolkit.git
   cd alkimiya-order-toolkit
   ```

2. Create a virtual environment and activate it:

   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```

3. Install the required packages:

   ```
   pip install -r requirements.txt
   ```

### Configuration

Create a `.env` file in the root directory and add the following environment variables:

```
ACCOUNT=your_ethereum_account_address
PRIVATE_KEY=your_private_key
CONTRACT_ADDRESS=your_contract_address
WEB3_HTTP_URL=your_web3_provider_url
```

### Running the Application

Run the main script to create and place an order:

```
python main.py
```

## Project Structure

```
alkimiya-order-toolkit/
├── contracts/               # Contract ABI files
├── config.py                # Configuration management
├── contract_calls.py        # Contract interaction functions
├── graphql_calls.py         # GraphQL queries and mutations
├── main.py                  # Main script for order creation
├── orders.py                # Order class definition
├── pools.py                 # PoolData class definition
├── utils.py                 # Utility functions
└── requirements.txt         # Python package dependencies
```

## Usage

### Creating an Order

The `create_order` function in `main.py` handles the creation of an order. It generates a unique order ID, calculates the requested and offered amounts based on the order direction, and signs the order.

### Placing an Order

The `place_order` function in `graphql_calls.py` sends the order to the Alkimiya API using a GraphQL mutation.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request with your changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
