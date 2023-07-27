chains = {
    'agoric': {
        'daemon': 'agd',
        'chain_id': 'agoric-3',
        'wallet_address': 'agoric1ku5sm2twlsywdrp4wz3kfwgyrtqtp0lpnfq92x',
        'password': 'my_secure_key_password',
        'key_name': 'wallet',
        'validator_address': 'agoricvaloper1ku5sm2twlsywdrp4wz3kfwgyrtqtp0lpr3nvk8',
        'endpoint': 'https://agoric.rpc.kjnodes.com:443',
        'rewards_threshold': 1_000_000,
        'balance_threshold': 10_000_000,
        'balance_leftover': 1_000_000,
        'fees': '7000ubld',
        'denom': 'ubld',
        'ibc_channel': 'channel-1',
        'osmosis_address': 'osmo14kjrxes0fnlt9edqadz3uqnpj8d2cl6e75fnrt',
        'osmosis_key_name': 'agoric',
        'osmosis_denom': 'ibc/2DA9C149E9AD2BD27FEFA635458FB37093C256C1A940392634A16BEA45262604',  # BLD
        "routes": [
            {"pool_id": 795, "token_out_denom": "uosmo"},  # BLD-OSMO
            {"pool_id": 678, "token_out_denom": "ibc/D189335C6E4A68B513C10AB227BF1C1D38C746766278BA3EEB4FB14124F1D858"}  # OSMO-USDC
        ]
    }
}
osmosis_endpoint = 'https://osmosis.rpc.kjnodes.com:443'
