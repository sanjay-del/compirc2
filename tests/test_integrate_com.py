from inspect import signature
import json
import os
from typing import Union, List

from iconsdk.builder.call_builder import CallBuilder
from iconsdk.builder.transaction_builder import TransactionBuilder, DeployTransactionBuilder, CallTransactionBuilder
from iconsdk.exception import AddressException
from iconsdk.libs.in_memory_zip import gen_deploy_data_content
from iconsdk.signed_transaction import SignedTransaction
from iconsdk.wallet.wallet import KeyWallet, Wallet
from iconservice import icon_service_engine
from iconservice.base.address import Address
from tbears.config.tbears_config import tbears_server_config, TConfigKey as TbConf
from tbears.libs.icon_integrate_test import Account
from tbears.libs.icon_integrate_test import IconIntegrateTestBase, SCORE_INSTALL_ADDRESS
from iconsdk.icon_service import IconService
from iconsdk.providers.http_provider import HTTPProvider

DIR_PATH = os.path.abspath(os.path.dirname(__file__))
SCORE_ADDRESS = "scoreAddress"

def get_key(my_dict: dict, value: Union[str, int]):
    return list(my_dict.keys())[list(my_dict.values()).index(value)]

class ScoreTestUtlis(IconIntegrateTestBase):
    def setUp(self, 
              genesis_accounts: List[Account],
              block_confirm_interval: int,
              network_only: bool = False,
              network_delay_ms: int = tbears_server_config[TbConf.NETWORK_DELAY_MS],
              icon_service : IconService = None, 
              nid : int =  3,
              tx_result_wait: int = 3
              ):
        super().setUp(genesis_accounts, block_confirm_interval,network_only, network_delay_ms)
        self.icon_service = icon_service
        self.nid = nid 
        self.tx_results_wait = tx_result_wait
        
    def deploy_tx(self, 
                  from_:KeyWallet,
                  to:str = SCORE_INSTALL_ADDRESS,
                  value: int = 0,
                  content: str = None,
                  params: dict = None) -> dict:
        signed_transaction = self.build_deploy_tx(from_,to, value, content, params)
        tx_result = self.process_transaction(signed_transaction, network = self.icon_service, block_confirm_interval=self.tx_results_wait)
        self.assertTrue('status' in tx_result, tx_result)
        self.assertEqual(1, tx_result['status'], f"Failure: {tx_result['failure']}" if tx_result['status'] == 0 else "")
        self.assertTrue('scoreAddress' in tx_result)

        return tx_result
    
    def build_deploy_tx(self,
                        from_: KeyWallet,
                        to: str = SCORE_INSTALL_ADDRESS,
                        value : int = 0,
                        content: str = None,
                        params: dict = None,
                        step_limit: int = 3_000_000_000,
                        nonce: int = 100) -> SignedTransaction:
        print(f"---------------------------Deploying contract: {content}---------------------------------------")
        params = {} if params is None else params
         
        transaction = DeployTransactionBuilder()\
            .from_(from_.get_address()) \
            .to(to) \
            .value(value) \
            .step_limit(step_limit) \
            .nid(self.nid) \
            .nonce(nonce) \
            .content_type("application/zip") \
            .content(gen_deploy_data_content(content)) \
            .params(params) \
            .build()
        signed_transaction = SignedTransaction(transaction, from_)
        return signed_transaction
        
    def build_tx(self, from_: KeyWallet, to: str, value: int = 0, method: str = None, params: dict = None) \
            -> SignedTransaction:
        params = {} if params is None else params
        tx = CallTransactionBuilder(
            from_=from_.get_address(),
            to=to,
            value=value,
            step_limit=3_000_000_000,
            nid=self.nid,
            nonce=5,
            method=method,
            params=params
        ).build()
        signed_transaction = SignedTransaction(tx, from_)
        return signed_transaction
    
    def call_tx(self, to: str, method: str, params: dict = None):
    
        params = {} if params is None else params
        call = CallBuilder(
            to=to,
            method=method,
            params=params
        ).build()
        response = self.process_call(call, self.icon_service)
        print(f"-----Reading method={method}, with params={params} on the {to} contract------")
        print(f"-------------------The output is: : {response}")
        return response
    

class TestCompIRC2(ScoreTestUtlis):
    SCORE_PROJECT = os.path.abspath(os.path.join(DIR_PATH, '..'))
    def setUp(self):
        self._wallet_setup()
        self.name = 'Dhewa'
        self.symbol = 'Dhe'
        self.decimals = 20 
        self.initialSupply = 10
        self.cap =  50
        self.paused = False
        
        params = {
        '_name':self.name,
        '_symbol':self.symbol, 
        '_decimals':self.decimals,  
        '_initialSupply':self.initialSupply, 
        '_cap':self.cap,
        '_paused':self.paused
        }
        super().setUp(genesis_accounts=self.genesis_account,
                      block_confirm_interval=2,
                      network_delay_ms=0,
                      network_only=True,
                      icon_service=IconService(HTTPProvider("http://127.0.0.1:9000", 3)),
                      nid=3,
                      tx_result_wait=4
                      )
        
        self._score_address = self.deploy_tx(self.genesis_account,params)['scoreAddress']
    
    def _wallet_setup(self):
        self.icx_factor = 10 ** 18
        self.user1: 'KeyWallet' = self._wallet_array[7]
        self.user2: 'KeyWallet' = self._wallet_array[8]
        self.genesis_account = [
            Account("test1", Address.from_string(self._test1.get_address()), 800_000_000 * self.icx_factor)
            ]

    
    # def test_score_update(self):
    #     # update SCORE
    #     tx_result = self.deploy_tx(to=self._score_address)

    #     self.assertEqual(self._score_address, tx_result['scoreAddress'])
    
    def test_total_supply(self):
        to = self._test1
        response = self.call_tx(to , 'totalSupply')
        self.assertEqual(self.initial_supply*10**self.decimals, response)