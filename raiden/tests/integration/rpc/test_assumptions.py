# -*- coding: utf-8 -*-
import os

import pytest
from ethereum import _solidity
from pyethapp.rpc_client import data_encoder, quantity_decoder

# pylint: disable=unused-argument,protected-access


def deploy_rpc_test_contract(deploy_client):
    here = os.path.dirname(os.path.relpath(__file__))
    contract_path = os.path.join(here, 'RpcTest.sol')
    contracts = _solidity.compile_file(contract_path, libraries=dict())

    contract_proxy = deploy_client.deploy_solidity_contract(
        deploy_client.sender,
        'RpcTest',
        contracts,
        libraries=dict(),
        constructor_parameters=None,
        contract_path=contract_path,
    )

    return contract_proxy


@pytest.mark.parametrize('blockchain_type', ['geth'])
def test_call_inexisting_address(deploy_client, blockchain_backend):
    """ A JSON RPC call to an inexisting address returns the empty string. """

    inexisting_address = '\x01\x02\x03\x04\x05' * 4

    assert deploy_client.eth_getCode(inexisting_address) == '0x'
    assert deploy_client.eth_call(sender=deploy_client.sender, to=inexisting_address) == ''


@pytest.mark.parametrize('blockchain_type', ['geth'])
def test_call_invalid_selector(deploy_client, blockchain_backend):
    """ A JSON RPC call to a valid address but with an invalid selector returns
    the empty string.
    """
    contract_proxy = deploy_rpc_test_contract(deploy_client)
    address = contract_proxy.address
    assert deploy_client.eth_getCode(address) != '0x'

    selector = contract_proxy.translator.encode_function_call('ret', args=[])
    next_byte = chr(ord(selector[0]) + 1)
    wrong_selector = next_byte + selector[1:]
    result = deploy_client.eth_call(
        sender=deploy_client.sender,
        to=address,
        data=wrong_selector,
    )
    assert result == ''


@pytest.mark.parametrize('blockchain_type', ['geth'])
def test_call_throws(deploy_client, blockchain_backend):
    """ A JSON RPC call to a function that throws returns the empty string. """
    contract_proxy = deploy_rpc_test_contract(deploy_client)

    address = contract_proxy.address
    assert deploy_client.eth_getCode(address) != '0x'

    assert contract_proxy.fail.call() == ''


@pytest.mark.parametrize('blockchain_type', ['geth'])
def test_transact_throws(deploy_client, blockchain_backend):
    """ A JSON RPC call to a function that throws returns uses all gas. """
    contract_proxy = deploy_rpc_test_contract(deploy_client)

    address = contract_proxy.address
    assert deploy_client.eth_getCode(address) != '0x'

    gas = contract_proxy.fail.estimate_gas()

    transaction_hex = contract_proxy.fail.transact(startgas=gas)
    transaction = transaction_hex.decode('hex')

    deploy_client.poll(transaction)

    receipt = deploy_client.call('eth_getTransactionReceipt', data_encoder(transaction))
    assert gas == quantity_decoder(receipt['gasUsed'])
