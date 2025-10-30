"""Monitor the status of a CCIP transaction until it is confirmed."""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence

from dotenv import load_dotenv
from web3 import Web3
from web3.contract.contract import ContractEvent
from web3.exceptions import TransactionNotFound

ROUTER_EVENT_ABI: List[dict[str, Any]] = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "messageId", "type": "bytes32"},
            {"indexed": True, "internalType": "uint64", "name": "destinationChainSelector", "type": "uint64"},
            {"indexed": False, "internalType": "address", "name": "sender", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "feeTokenAmount", "type": "uint256"},
            {"indexed": False, "internalType": "address", "name": "feeToken", "type": "address"},
        ],
        "name": "CCIPSendRequested",
        "type": "event",
    }
]


@dataclass
class EnvConfig:
    rpc_url: str
    router_address: str

    @classmethod
    def from_env(cls) -> "EnvConfig":
        load_dotenv()
        try:
            rpc_url = os.environ["RPC_URL"].strip()
            router_address = Web3.to_checksum_address(os.environ["CCIP_ROUTER_ADDRESS"].strip())
        except KeyError as exc:
            missing = exc.args[0]
            raise SystemExit(f"Missing required environment variable: {missing}") from exc
        except ValueError as exc:
            raise SystemExit(f"Invalid environment variable format: {exc}") from exc
        return cls(rpc_url=rpc_url, router_address=router_address)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor a CCIP transaction hash.")
    parser.add_argument("--tx", required=True, help="Transaction hash to monitor (0x-prefixed).")
    parser.add_argument("--interval", type=float, default=10.0, help="Polling interval in seconds.")
    parser.add_argument("--timeout", type=float, default=900.0, help="Maximum time to wait before exiting (seconds).")
    return parser.parse_args(argv)


def connect_web3(rpc_url: str) -> Web3:
    provider = Web3(Web3.HTTPProvider(rpc_url))
    if not provider.is_connected():
        raise SystemExit(f"Unable to connect to RPC provider at {rpc_url}")
    return provider


def poll_transaction(web3: Web3, tx_hash: str, interval: float, timeout: float) -> Optional[dict[str, Any]]:
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            print("Timeout reached while waiting for transaction confirmation.")
            return None

        try:
            receipt = web3.eth.get_transaction_receipt(tx_hash)
            return receipt
        except TransactionNotFound:
            print(f"[{elapsed:.0f}s] Transaction pending... next check in {interval}s")
            time.sleep(interval)


def decode_router_events(contract_event: ContractEvent, receipt: dict[str, Any]) -> None:
    try:
        events = contract_event().process_receipt(receipt)
    except ValueError as exc:
        print(f"Unable to decode router events: {exc}")
        events = []

    if not events:
        print("No CCIP router events decoded. Inspect raw logs for details:")
        for idx, log in enumerate(receipt.get("logs", [])):
            print(f" - Log {idx}: address={log['address']} topics={log['topics']}")
        return

    for event in events:
        args = event["args"]
        print("Decoded CCIPSendRequested event:")
        print(f" - messageId: {args.get('messageId')}")
        print(f" - destination selector: {args.get('destinationChainSelector')}")
        print(f" - sender: {args.get('sender')}")
        print(f" - fee token: {args.get('feeToken')}")
        print(f" - fee amount: {args.get('feeTokenAmount')}")


def main(argv: Optional[Sequence[str]] = None) -> None:
    try:
        config = EnvConfig.from_env()
    except SystemExit as exc:
        print(exc)
        sys.exit(1)

    args = parse_args(argv if argv is not None else sys.argv[1:])

    web3 = connect_web3(config.rpc_url)
    router = web3.eth.contract(address=config.router_address, abi=ROUTER_EVENT_ABI)

    print(f"Monitoring transaction {args.tx} on RPC {config.rpc_url}")
    receipt = poll_transaction(web3, args.tx, args.interval, args.timeout)
    if receipt is None:
        sys.exit(1)

    status_text = "Success" if receipt.get("status") == 1 else "Failure"
    print(f"Transaction status: {status_text}")
    print(f"Block number: {receipt.get('blockNumber')}")
    print(f"Gas used: {receipt.get('gasUsed')}")

    decode_router_events(router.events.CCIPSendRequested, receipt)


if __name__ == "__main__":
    main()
