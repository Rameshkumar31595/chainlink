# Chainlink CCIP Python Integration Example

The Cross-Chain Interoperability Protocol (CCIP) is Chainlink's unified framework for secure cross-chain messaging and token transfers. By building on CCIP, developers can send arbitrary data or assets between blockchains without managing bespoke bridge infrastructure. This repository demonstrates how to integrate CCIP in a Python 3.9+ environment using familiar tooling like `web3.py` and `python-dotenv`.

---

## Why Cross-Chain Messaging Matters

Modern decentralized applications frequently span multiple blockchain networks. CCIP abstracts the complexity of routing data and value across chains by providing:

- **Secure message delivery** backed by Chainlink's decentralized oracle network.
- **Token transfers** that handle on-chain approvals, fee payments, and message execution.
- **Unified interfaces** for a variety of supported chains (e.g., Ethereum Sepolia, Polygon Amoy, Arbitrum Sepolia).

This example gives Python developers a quick starting point for reading CCIP router state, sending cross-chain messages, and monitoring transaction status.

---

## Repository Structure

```
ccip-python-example/
├── README.md              # Documentation and usage guide
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── ccip_read.py           # Script to inspect CCIP router configuration
├── ccip_send.py           # Script to send CCIP messages or token transfers
└── ccip_monitor.py        # Script to monitor message delivery receipts
```

---

## Prerequisites

1. **Python**: Version 3.9 or later.
2. **Virtual environment**: Optional but recommended (e.g., `python3 -m venv .venv`).
3. **RPC provider**: An RPC URL for the source network (e.g., Sepolia via Infura or Alchemy).
4. **Private key**: A funded account on the source chain for signing transactions.
5. **CCIP Router address**: Check the [Chainlink CCIP documentation](https://docs.chain.link/ccip) for the latest addresses per network.
6. **Destination chain selector**: A numeric identifier for the target chain (Sepolia → Polygon Amoy example shown below).

> ⚠️ **Security reminder:** Never commit real private keys. Use `.env` to load sensitive values at runtime.

---

## Setup Instructions

1. **Clone or copy this directory** into your development workspace.

2. **Create and activate a virtual environment (optional but recommended):**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   - Duplicate `.env.example` to `.env`.
   - Fill in the placeholders with your own values.

   ```bash
   cp .env.example .env
   nano .env  # or use your preferred editor
   ```

---

## Script Overview & Usage

### 1. `ccip_read.py`
Reads on-chain configuration from the CCIP Router, such as supported destination chains and fee tokens.

```bash
python3 ccip_read.py
```

**Expected output (example):**
```
Connecting to RPC: https://sepolia.infura.io/v3/... 
Router address: 0xYourRouterAddress
Supported destination chains:
 - 16015286601757825753
Fee tokens:
 - 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE
```

### 2. `ccip_send.py`
Constructs, signs, and broadcasts a CCIP message or token transfer. The script quotes fees, surfaces the gas estimate, and waits for transaction receipt.

```bash
python3 ccip_send.py --amount 0 --message "Hello, Polygon!"
```

**Expected output (example):**
```
Quoted CCIP fee: 0.0021 ETH (raw: 2100000000000000)
Estimated gas: 182345
Prepared transaction:
{'chainId': 11155111, 'data': '0x...', ...}
Broadcasted transaction: 0xabc123...
Waiting for confirmation...
Transaction confirmed in block 5123456
```

### 3. `ccip_monitor.py`
Continuously polls for a specific transaction hash, printing delivery status and logs for troubleshooting.

```bash
python3 ccip_monitor.py --tx 0xabc123...
```

**Expected output (example):**
```
Polling transaction 0xabc123...
Status: Pending...
Status: Confirmed on source chain (block 5123456)
Message execution logs:
 - CCIPSendRequested(...)
 - CCIPSendSent(...)
```

---

## Connecting to Testnets

1. **Select test networks:** For example, sending from Ethereum Sepolia to Polygon Amoy.
2. **Set `.env` values:**
   - `RPC_URL` → Sepolia RPC endpoint.
   - `CCIP_ROUTER_ADDRESS` → Sepolia CCIP Router.
   - `DESTINATION_CHAIN_SELECTOR` → `16015286601757825753` (Sepolia → Polygon Amoy selector).
   - `RECEIVER_ADDRESS` → Destination wallet or contract address on Polygon.
3. **Fund your sender account:** Acquire Sepolia ETH from a faucet for gas fees.
4. **Ensure destination chain has liquidity:** For token transfers, the receiver must handle the delivered asset.

Consult the [Chainlink CCIP Testnet Guide](https://docs.chain.link/ccip/supported-networks/testnet) for up-to-date network IDs, router addresses, and selector values.

---

## Troubleshooting Tips

- **Connection errors:** Verify your `RPC_URL` and that your provider allows mainnet/testnet access.
- **Insufficient funds:** Ensure your private key controls an account with enough testnet ETH for gas.
- **Transaction failures:** Inspect the transaction receipt logs printed by `ccip_monitor.py` for revert reasons.
- **ABI updates:** If Chainlink releases a new router, update the ABI JSON in the scripts accordingly.

---

## How to Contribute This Example to the Chainlink Docs Repository

1. **Fork** the [Chainlink repository](https://github.com/smartcontractkit/chainlink) and clone your fork locally.
2. **Create a new branch**, for example `docs/ccip-python-example`.
3. **Copy** the `ccip-python-example` directory into the `docs/` (or relevant) folder of your fork.
4. **Install dependencies** and run any documentation linting or formatting scripts if required.
5. **Commit** your changes with a message referencing issue `#19807`, e.g., `docs: add CCIP Python integration example (#19807)`.
6. **Open a pull request** against the upstream repository, linking to [GitHub issue #19807](https://github.com/smartcontractkit/chainlink/issues/19807) in the PR description.
7. **Respond to reviewer feedback** and iterate until the PR is approved and merged.

By following these steps you will help expand the Chainlink documentation with Python resources for CCIP developers.

---

## Next Steps

- Explore advanced CCIP features like off-chain reporting of message status.
- Integrate the scripts into your CI/CD pipeline for automated cross-chain operations.
- Join the [Chainlink Discord](https://discord.gg/chainlink) for community support and updates.

Happy building! 🚀
