"""Send a cross-chain message or token transfer via Chainlink CCIP."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv
from eth_abi import encode
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.contract.contract import Contract
from web3.exceptions import ContractLogicError

# CCIP Router ABI subset required for sending messages.
ROUTER_ABI: List[dict[str, Any]] = [
    {
        "inputs": [
            {"internalType": "uint64", "name": "destChainSelector", "type": "uint64"},
            {
                "components": [
                    {"internalType": "bytes", "name": "receiver", "type": "bytes"},
                    {"internalType": "bytes", "name": "data", "type": "bytes"},
                    {
                        "components": [
                            {"internalType": "address", "name": "token", "type": "address"},
                            {"internalType": "uint256", "name": "amount", "type": "uint256"},
                        ],
                        "internalType": "struct Client.EVMTokenAmount[]",
                        "name": "tokenAmounts",
                        "type": "tuple[]",
                    },
                    {"internalType": "address", "name": "feeToken", "type": "address"},
                    {"internalType": "bytes", "name": "extraArgs", "type": "bytes"},
                ],
                "internalType": "struct Client.EVM2AnyMessage",
                "name": "message",
                "type": "tuple",
            },
        ],
        "name": "ccipSend",
        "outputs": [
            {"internalType": "bytes32", "name": "messageId", "type": "bytes32"},
        ],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint64", "name": "destChainSelector", "type": "uint64"},
            {
                "components": [
                    {"internalType": "bytes", "name": "receiver", "type": "bytes"},
                    {"internalType": "bytes", "name": "data", "type": "bytes"},
                    {
                        "components": [
                            {"internalType": "address", "name": "token", "type": "address"},
                            {"internalType": "uint256", "name": "amount", "type": "uint256"},
                        ],
                        "internalType": "struct Client.EVMTokenAmount[]",
                        "name": "tokenAmounts",
                        "type": "tuple[]",
                    },
                    {"internalType": "address", "name": "feeToken", "type": "address"},
                    {"internalType": "bytes", "name": "extraArgs", "type": "bytes"},
                ],
                "internalType": "struct Client.EVM2AnyMessage",
                "name": "message",
                "type": "tuple",
            },
        ],
        "name": "getFee",
        "outputs": [
            {"internalType": "uint256", "name": "fee", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
EVM_EXTRA_ARGS_VERSION = 1


@dataclass
class EnvConfig:
    """Environment variables used by the script."""

    rpc_url: str
    router_address: str
    private_key: str
    destination_selector: int
    receiver_address: str

    @classmethod
    def from_env(cls) -> "EnvConfig":
        load_dotenv()
        try:
            rpc_url = os.environ["RPC_URL"].strip()
            router_address = Web3.to_checksum_address(os.environ["CCIP_ROUTER_ADDRESS"].strip())
            private_key = os.environ["PRIVATE_KEY"].strip()
            destination_selector = int(os.environ["DESTINATION_CHAIN_SELECTOR"].strip())
            receiver_address = Web3.to_checksum_address(os.environ["RECEIVER_ADDRESS"].strip())
        except KeyError as exc:
            missing = exc.args[0]
            raise SystemExit(f"Missing required environment variable: {missing}") from exc
        except ValueError as exc:
            raise SystemExit(f"Invalid environment variable format: {exc}") from exc
        return cls(
            rpc_url=rpc_url,
            router_address=router_address,
            private_key=private_key,
            destination_selector=destination_selector,
            receiver_address=receiver_address,
        )


def connect_web3(rpc_url: str) -> Web3:
    provider = Web3(Web3.HTTPProvider(rpc_url))
    if not provider.is_connected():
        raise SystemExit(f"Unable to connect to RPC provider at {rpc_url}")
    return provider


def get_account(private_key: str) -> LocalAccount:
    try:
        account = Account.from_key(private_key)
    except ValueError as exc:
        raise SystemExit(f"Invalid private key: {exc}") from exc
    return account


def encode_receiver_address(receiver: str) -> bytes:
    """Encode an EVM address as bytes for the CCIP receiver field."""

    return encode(["address"], [receiver])


def encode_extra_args(gas_limit: int) -> bytes:
    """Encode CCIP extraArgs using EVMExtraArgsV1."""

    if gas_limit <= 0:
        raise SystemExit("Gas limit must be greater than zero for extraArgs.")
    return encode(["uint16", "uint256"], [EVM_EXTRA_ARGS_VERSION, gas_limit])


def build_message(
    receiver: str,
    payload: bytes,
    fee_token: Optional[str],
    token_address: Optional[str],
    token_amount: int,
    gas_limit: int,
) -> Tuple[bytes, bytes, List[Dict[str, Any]], str, bytes]:
    """Construct the EVM2AnyMessage tuple expected by the router."""

    encoded_receiver = encode_receiver_address(receiver)
    token_amounts: List[Dict[str, Any]] = []
    if token_amount > 0:
        if not token_address:
            raise SystemExit("A token address must be provided when --amount is greater than 0.")
        token_amounts.append(
            {
                "token": Web3.to_checksum_address(token_address),
                "amount": token_amount,
            }
        )

    final_fee_token: str
    if fee_token is None or fee_token.strip() == "":
        final_fee_token = ZERO_ADDRESS
    elif fee_token.lower() == "native":
        final_fee_token = ZERO_ADDRESS
    else:
        final_fee_token = Web3.to_checksum_address(fee_token)

    extra_args = encode_extra_args(gas_limit)

    message = (
        encoded_receiver,
        payload,
        token_amounts,
        final_fee_token,
        extra_args,
    )
    return message


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("Amount must be non-negative.")
    return parsed


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a CCIP cross-chain message.")
    parser.add_argument("--message", default="Hello from Python!", help="UTF-8 string payload to deliver on the destination chain.")
    parser.add_argument("--amount", type=positive_int, default=0, help="Token amount (in smallest units) to send with the message.")
    parser.add_argument("--token-address", dest="token_address", help="ERC-20 token address to transfer (required when --amount > 0).")
    parser.add_argument("--fee-token", dest="fee_token", help="Token to pay CCIP fees with. Use 'native' or omit to pay in native gas token.")
    parser.add_argument("--gas-limit", type=positive_int, default=200_000, help="Gas limit for destination execution encoded in extraArgs.")
    parser.add_argument("--dry-run", action="store_true", help="Build the transaction without broadcasting it.")
    return parser.parse_args(argv)


def estimate_fee(router: Contract, selector: int, message: tuple) -> int:
    try:
        return router.functions.getFee(selector, message).call()
    except ContractLogicError as exc:
        raise SystemExit(f"Router reverted while quoting fee: {exc}") from exc


def prepare_transaction(
    web3: Web3,
    router: Contract,
    selector: int,
    message: tuple,
    sender: str,
    fee: int,
) -> Tuple[dict[str, Any], int]:
    value = fee if message[3].lower() == ZERO_ADDRESS else 0
    base_tx = {
        "from": sender,
        "nonce": web3.eth.get_transaction_count(sender),
        "chainId": web3.eth.chain_id,
        "value": value,
    }

    try:
        gas_estimate = router.functions.ccipSend(selector, message).estimate_gas(base_tx)
    except ContractLogicError as exc:
        raise SystemExit(f"Gas estimation failed: {exc}") from exc

    priority_fee = web3.to_wei("2", "gwei")
    base_fee = web3.eth.gas_price
    max_fee_per_gas = base_fee + priority_fee

    tx = router.functions.ccipSend(selector, message).build_transaction(
        {
            **base_tx,
            "gas": gas_estimate,
            "maxFeePerGas": max_fee_per_gas,
            "maxPriorityFeePerGas": priority_fee,
        }
    )
    return tx, gas_estimate


def main(argv: Optional[Sequence[str]] = None) -> None:
    try:
        config = EnvConfig.from_env()
    except SystemExit as exc:
        print(exc)
        sys.exit(1)

    args = parse_args(argv if argv is not None else sys.argv[1:])

    web3 = connect_web3(config.rpc_url)
    router = web3.eth.contract(address=config.router_address, abi=ROUTER_ABI)
    account = get_account(config.private_key)

    payload = args.message.encode("utf-8")
    message = build_message(
        receiver=config.receiver_address,
        payload=payload,
        fee_token=args.fee_token,
        token_address=args.token_address,
        token_amount=args.amount,
        gas_limit=args.gas_limit,
    )

    fee = estimate_fee(router, config.destination_selector, message)
    print(f"Quoted CCIP fee: {Web3.from_wei(fee, 'ether')} ETH (raw: {fee})")

    tx, gas_estimate = prepare_transaction(
        web3,
        router,
        config.destination_selector,
        message,
        account.address,
        fee,
    )

    print(f"Estimated gas: {gas_estimate}")
    print("Prepared transaction:")
    print(tx)

    if args.dry_run:
        print("Dry run enabled. Transaction not broadcast.")
        return

    signed = account.sign_transaction(tx)
    tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
    print(f"Broadcasted transaction: {tx_hash.hex()}")

    print("Waiting for confirmation...")
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
    print(f"Transaction confirmed in block {receipt.blockNumber}")
    print(f"Gas used: {receipt.gasUsed}")
    print(f"CCIP message ID (topic0 data): {receipt.logs[0].topics[1].hex() if receipt.logs else 'n/a'}")


if __name__ == "__main__":
    main()
