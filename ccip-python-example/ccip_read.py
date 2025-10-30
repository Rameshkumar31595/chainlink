"""Utility script to inspect the Chainlink CCIP Router configuration."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Iterable, List

from dotenv import load_dotenv
from web3 import Web3
from web3.contract.contract import ContractFunction
from web3.exceptions import BadFunctionCallOutput, ContractLogicError

# Minimal subset of the CCIP Router ABI that we need for read-only calls.
# The full ABI can be obtained from the official Chainlink documentation or block explorer.
ROUTER_ABI: List[dict[str, Any]] = [
    {
        "inputs": [],
        "name": "getFeeTokens",
        "outputs": [
            {
                "internalType": "address[]",
                "name": "",
                "type": "address[]",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getSupportedTokens",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "token", "type": "address"},
                    {"internalType": "uint64", "name": "destChainSelector", "type": "uint64"},
                ],
                "internalType": "struct IRouter.TokenSupport[]",
                "name": "",
                "type": "tuple[]",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {
                "internalType": "uint64",
                "name": "destChainSelector",
                "type": "uint64",
            }
        ],
        "name": "isChainSupported",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getWrappedNativeToken",
        "outputs": [
            {"internalType": "address", "name": "tokenAddress", "type": "address"},
            {"internalType": "bool", "name": "available", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


@dataclass
class EnvConfig:
    """Container for strongly-typed environment configuration."""

    rpc_url: str
    router_address: str
    destination_selector: int

    @classmethod
    def from_env(cls) -> "EnvConfig":
        load_dotenv()
        try:
            rpc_url = os.environ["RPC_URL"].strip()
            router_address = Web3.to_checksum_address(os.environ["CCIP_ROUTER_ADDRESS"].strip())
            destination_selector = int(os.environ["DESTINATION_CHAIN_SELECTOR"].strip())
        except KeyError as exc:  # Missing environment variable
            missing = exc.args[0]
            raise SystemExit(f"Missing required environment variable: {missing}") from exc
        except ValueError as exc:  # Invalid selector or address formatting
            raise SystemExit(f"Invalid environment variable format: {exc}") from exc
        return cls(rpc_url=rpc_url, router_address=router_address, destination_selector=destination_selector)


def connect_web3(rpc_url: str) -> Web3:
    """Create a Web3 HTTP provider and verify the connection."""

    provider = Web3(Web3.HTTPProvider(rpc_url))
    if not provider.is_connected():
        raise SystemExit(f"Unable to connect to RPC provider at {rpc_url}")
    return provider


def safe_call(function_factory: Callable[..., ContractFunction], *args: Any) -> Any:
    """Execute a read-only contract call while gracefully handling common errors."""

    try:
        return function_factory(*args).call()
    except BadFunctionCallOutput:
        fn_name = getattr(function_factory, "fn_name", repr(function_factory))
        print(f"[warn] Function {fn_name} is not available on the target router.")
    except ContractLogicError as exc:
        fn_name = getattr(function_factory, "fn_name", repr(function_factory))
        print(f"[warn] Router reverted while executing {fn_name}: {exc}")
    return None


def format_addresses(values: Iterable[str]) -> str:
    """Format a list of addresses for human-friendly display."""

    return "\n".join(f" - {value}" for value in values)


def main() -> None:
    """Entrypoint for the ccip_read script."""

    try:
        config = EnvConfig.from_env()
    except SystemExit as exc:
        print(exc)
        sys.exit(1)

    web3 = connect_web3(config.rpc_url)
    router = web3.eth.contract(address=config.router_address, abi=ROUTER_ABI)

    print(f"Connecting to RPC: {config.rpc_url}")
    print(f"Router address: {config.router_address}")

    fee_tokens = safe_call(router.functions.getFeeTokens)
    if isinstance(fee_tokens, list):
        print("Fee tokens registered on this router:")
        print(format_addresses(fee_tokens) or " - <none>")

    supported_tokens = safe_call(router.functions.getSupportedTokens)
    if supported_tokens:
        print("\nToken support table (token → destination selector):")
        for entry in supported_tokens:
            token_address = entry[0]
            dest_selector = entry[1]
            print(f" - {token_address} → {dest_selector}")

    is_supported = safe_call(router.functions.isChainSupported, config.destination_selector)
    if isinstance(is_supported, bool):
        status = "yes" if is_supported else "no"
        print(f"\nIs destination selector {config.destination_selector} supported? {status}")

    wrapped_native = safe_call(router.functions.getWrappedNativeToken)
    if wrapped_native:
        token_address, available = wrapped_native
        print("\nWrapped native token:")
        print(f" - address: {token_address}")
        print(f" - available: {available}")

    print("\nTip: update ROUTER_ABI with additional functions as needed for deeper inspection.")


if __name__ == "__main__":
    main()
