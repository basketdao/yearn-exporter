from collections import defaultdict
from dataclasses import dataclass
from typing import List

from brownie import Contract
from brownie.network.contract import InterfaceContainer
from joblib import Parallel, delayed

from yearn.events import contract_creation_block
from yearn.mutlicall import fetch_multicall, multicall_matrix
from yearn.prices import magic

IEARN = {
    # v1 - deprecated
    # v2
    "yDAIv2": "0x16de59092dAE5CcF4A1E6439D611fd0653f0Bd01",
    "yUSDCv2": "0xd6aD7a6750A7593E092a9B218d66C0A814a3436e",
    "yUSDTv2": "0x83f798e925BcD4017Eb265844FDDAbb448f1707D",
    "ysUSDv2": "0xF61718057901F84C4eEC4339EF8f0D86D2B45600",
    "yTUSDv2": "0x73a052500105205d34daf004eab301916da8190f",
    "yWBTCv2": "0x04Aa51bbcB46541455cCF1B8bef2ebc5d3787EC9",
    # v3
    "yDAIv3": "0xC2cB1040220768554cf699b0d863A3cd4324ce32",
    "yUSDCv3": "0x26EA744E5B887E5205727f55dFBE8685e3b21951",
    "yUSDTv3": "0xE6354ed5bC4b393a5Aad09f21c46E101e692d447",
    "yBUSDv3": "0x04bC0Ab673d88aE9dbC9DA2380cB6B79C4BCa9aE",
}


@dataclass
class iEarn:
    name: str
    contract: InterfaceContainer
    token: InterfaceContainer
    decimals: int

    def describe(self):
        raise NotImplementedError("Use optimized `describe_iearn` with multiple instances.")


def load_iearn() -> List[iEarn]:
    contracts = [Contract(x) for x in IEARN.values()]
    output = multicall_matrix(contracts, ["token", "decimals"])
    return [iEarn(name, addr, output[addr]["token"], output[addr]["decimals"]) for name, addr in zip(IEARN, contracts)]


def describe_iearn(iearn: List[iEarn], block=None) -> dict:
    contracts = [x.contract for x in iearn]
    if block:
        contracts = [contract for contract in contracts if contract_creation_block(str(contract)) < block]
    
    results = multicall_matrix(contracts, ["totalSupply", "pool", "getPricePerFullShare", "balance"], block=block)
    output = defaultdict(dict)

    for i in iearn:
        res = results[i.contract]
        price = magic.get_price(i.token, block=block)
        output[i.name] = {
            "total supply": res["totalSupply"] / 10 ** i.decimals,
            "available balance": res["balance"] / 10 ** i.decimals,
            "pooled balance": res["pool"] / 10 ** i.decimals,
            "price per share": res["getPricePerFullShare"] / 1e18,
            "token price": price,
            "tvl": res["pool"] / 10 ** i.decimals * price,
        }

    return dict(output)


def total_value_at(iearns, block=None):
    if block:
        iearns = [earn for earn in iearns if contract_creation_block(str(earn.contract)) < block]

    prices = Parallel(8, "threading")(delayed(magic.get_price)(earn.token, block=block) for earn in iearns)
    results = fetch_multicall(*[[earn.contract, "pool"] for earn in iearns], block=block)
    return {earn.name: assets * price / 10 ** earn.decimals for earn, assets, price in zip(iearns, results, prices)}
