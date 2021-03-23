from brownie import Contract
from cachetools.func import ttl_cache
from yearn.mutlicall import fetch_multicall


@ttl_cache(ttl=3600)
def get_markets():
    comptroller = Contract("0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B")
    creamtroller = Contract('0x3d5BC3c8d13dcB8bF317092d84783c2697AE9258')
    ironbankroller = Contract("0xAB1c342C7bf5Ec5F02ADEA1c2270670bCa144CbB")
    
    results = fetch_multicall(
        [comptroller, 'getAllMarkets'],
        [creamtroller, 'getAllMarkets'],
        [ironbankroller, 'getAllMarkets'],
    )
    names = ['compound', 'cream', 'ironbank']
    return dict(zip(names, results))


def is_compound_market(addr):
    markets = get_markets()
    return any(addr in market for market in markets.values())
