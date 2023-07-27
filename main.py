import json
import logging
from time import sleep

from subprocess import run
from config import chains, osmosis_endpoint, cooldown

BIN_DIR = "/usr/local/bin/"

logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)


def get_balance(daemon: str, endpoint: str, wallet_address: str, denom: str):
    command = f"{BIN_DIR}{daemon} q bank balances {wallet_address} --node {endpoint} --output json"
    logger.debug(f"Get balance: {command}")
    result = run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 1:
        logger.info(f"Get balance: Failed!")
        logger.info(command)
        return None

    response = json.loads(result.stdout)
    for balance in response['balances']:
        if balance['denom'] == denom:
            logger.info(f"Token balance: {balance['amount']} {balance['denom']}")
            return int(balance['amount'])

    logger.info("Token balance not found!")
    return 0


# First get the reward balance. If the reward is more than the threshold, then withdraw the rewards
def withdraw_rewards(daemon: str,
                     endpoint: str,
                     wallet_address: str,
                     validator_address: str,
                     rewards_threshold: int,
                     fees: str,
                     chain_id: str,
                     key_name: str,
                     password: str,
                     denom: str):
    command = f"{BIN_DIR}{daemon} q distribution rewards {wallet_address} {validator_address} " \
              f"--node {endpoint} " \
              f"--output json"
    logger.debug(f"Get rewards: {command}")
    result = run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 1:
        logger.info(f"Get rewards: Failed!")
        logger.info(command)
        return None

    response = json.loads(result.stdout)
    rewards = 0

    for reward in response['rewards']:
        if reward['denom'] == denom:
            rewards = int(float(reward['amount']))
            break

    logger.info(f"Available rewards: {rewards} {denom}")

    if rewards >= rewards_threshold:
        logger.info(f"Withdrawing rewards...")
        command = f"echo {password} | {BIN_DIR}{daemon} tx distribution withdraw-rewards {validator_address} " \
                  f"--commission " \
                  f"--from {key_name} " \
                  f"--chain-id {chain_id} " \
                  f"--node {endpoint} " \
                  f"--fees {fees} " \
                  f"--output json " \
                  f"--gas auto " \
                  f"--gas-adjustment 1.3 " \
                  f"--yes"
        logger.debug(f"Withdraw rewards: {command}")
        result = run(command, shell=True, capture_output=True, text=True)

        # Cooldown after submitting transaction
        sleep(cooldown)

        if result.returncode == 1:
            logger.info(f"Withdraw rewards: Failed!")
            logger.info(command)
            return None

        response = json.loads(result.stdout)
        print(response)
        return response

    else:
        logger.info(f"Rewards did not reach threshold! ({rewards_threshold} {denom})")
        return None


# First get the balance. If the balance is more than the threshold, then transfer to Osmosis via IBC
def transfer_to_osmosis(daemon: str,
                        endpoint: str,
                        wallet_address: str,
                        denom: str,
                        balance_threshold: int,
                        balance_leftover: int,
                        password: str,
                        ibc_channel: str,
                        osmosis_address: str,
                        key_name: str,
                        chain_id: str,
                        fees: str):

    balance = get_balance(daemon=daemon,
                          endpoint=endpoint,
                          wallet_address=wallet_address,
                          denom=denom)

    if balance >= balance_threshold:
        withdrawal_amount = balance - balance_leftover
        command = f"echo {password} | {BIN_DIR}{daemon} tx ibc-transfer transfer transfer " \
                  f"{ibc_channel} {osmosis_address} {withdrawal_amount}{denom} " \
                  f"--from {key_name} " \
                  f"--chain-id {chain_id} " \
                  f"--node {endpoint} " \
                  f"--fees {fees} " \
                  f"--output json " \
                  f"--gas auto " \
                  f"--gas-adjustment 1.3 " \
                  f"--yes"
        logger.debug(f"Transfer to Osmosis: {command}")
        logger.info(f"Transfer {withdrawal_amount} {denom} to {osmosis_address}...")
        result = run(command, shell=True, capture_output=True, text=True)

        # Cooldown after submitting transaction
        sleep(cooldown*2)

        if result.returncode == 1:
            logger.info(f"Transfer to Osmosis: Failed!")
            logger.info(command)
            return None

        response = json.loads(result.stdout)
        print(response)
        return response

    else:
        logger.info(f"Balance did not reach threshold! ({balance_threshold} {denom})")
        return None


# First get the token balance on Osmosis. If the balance is more than the threshold, then make swap-exact-amount to USDC
def swap_to_usdc(daemon: str,
                 endpoint: str,
                 wallet_address: str,
                 denom: str,
                 balance_threshold: int,
                 password: str,
                 routes: list,
                 chain_id: str,
                 key_name: str,
                 fees: str):

    # Get token balance
    balance = get_balance(daemon=daemon,
                          endpoint=endpoint,
                          wallet_address=wallet_address,
                          denom=denom)

    # Estimate Swap Exact Amount In USDC
    if balance >= balance_threshold:
        command = f"echo {password} | {BIN_DIR}{daemon} query poolmanager estimate-swap-exact-amount-in " \
                  f"{routes[0]['pool_id']} {wallet_address} {balance}{denom} " \
                  f"--swap-route-pool-ids {','.join([str(x['pool_id']) for x in routes])} " \
                  f"--swap-route-denoms {','.join([str(x['token_out_denom']) for x in routes])} " \
                  f"--node {endpoint} " \
                  f"--output json"
        logger.debug(f"Estimate Swap Exact Amount In USDC: {command}")
        result = run(command, shell=True, capture_output=True, text=True)

        if result.returncode == 1:
            logger.info(f"Estimate Swap Exact Amount In USDC: Failed!")
            return None

        estimated_usdc = json.loads(result.stdout)['token_out_amount']
        logger.info(f"Estimated {balance}{denom} to {estimated_usdc}{routes[-1]['token_out_denom']}...")

        # Swap-exact-amount-in USDC
        command = f"echo {password} | {BIN_DIR}{daemon} tx poolmanager swap-exact-amount-in " \
                  f"{balance}{denom} {estimated_usdc} " \
                  f"--swap-route-pool-ids {','.join([str(x['pool_id']) for x in routes])} " \
                  f"--swap-route-denoms {','.join([str(x['token_out_denom']) for x in routes])} " \
                  f"--node {endpoint} " \
                  f"--from {key_name} " \
                  f"--chain-id {chain_id} " \
                  f"--fees {fees} " \
                  f"--yes " \
                  f"--output json"
        logger.debug(f"Swap Exact Amount In USDC: {command}")
        logger.info(f"Swapping {balance}{denom} to {estimated_usdc}{routes[-1]['token_out_denom']}...")
        result = run(command, shell=True, capture_output=True, text=True)

        # Cooldown after submitting transaction
        sleep(cooldown)

        if result.returncode == 1:
            logger.info(f"Swap Exact Amount In USDC: Failed!")
            return None

        response = json.loads(result.stdout)
        print(response)
        return response

    else:
        logger.info(f"Balance did not reach threshold! ({balance_threshold} {denom})")
        return None


def main():
    for k, v in chains.items():
        print(f'[{k.upper()}]\n')

        # Withdraw rewards
        withdraw_rewards(daemon=v['daemon'],
                         endpoint=v['endpoint'],
                         wallet_address=v['wallet_address'],
                         validator_address=v['validator_address'],
                         rewards_threshold=v['rewards_threshold'],
                         fees=v['fees'],
                         chain_id=v['chain_id'],
                         key_name=v['key_name'],
                         password=v['password'],
                         denom=v['denom'])

        # Transfer tokens to Osmosis
        transfer_to_osmosis(daemon=v['daemon'],
                            endpoint=v['endpoint'],
                            wallet_address=v['wallet_address'],
                            fees=v['fees'],
                            chain_id=v['chain_id'],
                            key_name=v['key_name'],
                            password=v['password'],
                            denom=v['denom'],
                            balance_leftover=v['balance_leftover'],
                            balance_threshold=v['balance_threshold'],
                            ibc_channel=v['ibc_channel'],
                            osmosis_address=v['osmosis_address'])

        # Swap exact amount in USDC
        swap_to_usdc(daemon='osmosisd',
                     endpoint=osmosis_endpoint,
                     wallet_address=v['osmosis_address'],
                     denom=v['osmosis_denom'],
                     balance_threshold=v['balance_threshold'],
                     password=v['password'],
                     routes=v['routes'],
                     chain_id='osmosis-1',
                     key_name=k,
                     fees='1000uosmo'
                     )

        print('')
        print('='*100)
        print('')


if __name__ == '__main__':
    main()
