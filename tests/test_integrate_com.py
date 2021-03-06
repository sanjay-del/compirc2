from inspect import signature
import json
import os
from typing import Union, List
from iconsdk.exception import JSONRPCException
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
        self.tx_result_wait = tx_result_wait
        
    def deploy_tx(self, 
                  from_:KeyWallet,
                  to:str = SCORE_INSTALL_ADDRESS,
                  value: int = 0,
                  content: str = None,
                  params: dict = None) -> dict:
        signed_transaction = self.build_deploy_tx(from_,to, value, content, params)
        tx_result = self.process_transaction(signed_transaction, network = self.icon_service, block_confirm_interval=self.tx_result_wait)
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
    
    def send_tx(self, from_: KeyWallet, to: str, value: int = 0, method: str = None, params: dict = None) -> dict:
        print(f"------------Calling {method}, with params={params} to {to} contract----------")
        signed_transaction = self.build_tx(from_, to, value, method, params)
        tx_result = self.process_transaction(signed_transaction, self.icon_service, self.tx_result_wait)

        self.assertTrue('status' in tx_result)
        self.assertEqual(1, tx_result['status'], f"Failure: {tx_result['failure']}" if tx_result['status'] == 0 else "")
        return tx_result

    
    
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
    
    def send_icx(self, from_: KeyWallet, to: str, value: int):
        previous_to_balance = self.get_balance(to)
        previous_from_balance = self.get_balance(from_.get_address())

        signed_icx_transaction = self.build_send_icx(from_, to, value)
        tx_result = self.process_transaction(signed_icx_transaction, self.icon_service, self.tx_result_wait)

        self.assertTrue('status' in tx_result, tx_result)
        self.assertEqual(1, tx_result['status'], f"Failure: {tx_result['failure']}" if tx_result['status'] == 0 else "")
        fee = tx_result['stepPrice'] * tx_result['cumulativeStepUsed']
        self.assertEqual(previous_to_balance + value, self.get_balance(to))
        self.assertEqual(previous_from_balance - value - fee, self.get_balance(from_.get_address()))

    def build_send_icx(self, from_: KeyWallet, to: str, value: int,
                       step_limit: int = 1000000, nonce: int = 3) -> SignedTransaction:
        send_icx_transaction = TransactionBuilder(
            from_=from_.get_address(),
            to=to,
            value=value,
            step_limit=step_limit,
            nid=self.nid,
            nonce=nonce
        ).build()
        signed_icx_transaction = SignedTransaction(send_icx_transaction, from_)
        return signed_icx_transaction

    def get_balance(self, address: str) -> int:
        if self.icon_service is not None:
            return self.icon_service.get_balance(address)
        params = {'address': Address.from_string(address)}
        response = self.icon_service_engine.query(method="icx_getBalance", params=params)
        return response
    
    
    def call_tx(self,from_:str,to: str, method: str, params: dict = None):
    
        params = {} if params is None else params
        call = CallBuilder(from_=from_,
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
        super().setUp(genesis_accounts=self.genesis_accounts,
                      block_confirm_interval=2,
                      network_delay_ms=0,
                      network_only=True,
                      icon_service=IconService(HTTPProvider("http://127.0.0.1:9000", 3)),
                      nid=3,
                      tx_result_wait=4
                      )
        self.send_icx(self._test1, self.user1.get_address(), 1_000_000 * self.icx_factor)
        self.send_icx(self._test1, self.user2.get_address(), 1_000_000 * self.icx_factor)
        self._deploy_conc(params)

    def _deploy_conc(self,params):
        self._score_address = self.deploy_tx(from_=self.user1,
                                             to = SCORE_INSTALL_ADDRESS,
                                             content = self.SCORE_PROJECT,
                                             params = params)['scoreAddress']
        
    def _wallet_setup(self):
        self.icx_factor = 10 ** 18
        self.user1: 'KeyWallet' = self._wallet_array[7]
        self.user2: 'KeyWallet' = self._wallet_array[8]
        self.genesis_accounts = [
            
            Account("user1", Address.from_string(self.user1.get_address()), 10_000_000 * self.icx_factor),
            Account("user2", Address.from_string(self.user2.get_address()), 10_000_000 * self.icx_factor),
            Account("test1", Address.from_string(self._test1.get_address()), 800_000_000 * self.icx_factor)
            ]
        
    
    
    def test_score_update(self):
        # update SCORE
        tx_result = self.deploy_tx(from_ = self.user1,
                                   to=self._score_address,
                                    content = self.SCORE_PROJECT)

        self.assertEqual(self._score_address, tx_result['scoreAddress'])
    
    def test_total_supply(self):
        params= {
        '_owner': self.user1.get_address()
        }
        print(f'score address {self.user1.get_address()}')
        print(f'score address {self._score_address}')
        response = self.call_tx(from_ = self.user1.get_address(),to=self._score_address , method ='balanceOf',
                                 params = params)
        self.assertEqual(hex(self.initialSupply*10**self.decimals), response)
        
    def test_minting(self):
        owner = self.user1
        receiver = self.user2.get_address()
        value = 50
        params = {
            '_to' : receiver,
            '_value' : value
        }
        resp=self.send_tx(from_= owner,
                           to = self._score_address, 
                           method = 'mintTo',
                           params = params)
        params = {
            "_owner" : receiver 
        }
        #value check
        res = self.call_tx(from_ = receiver,
                            to = self._score_address,
                           method = 'balanceOf',
                           params = params)
        self.assertEqual(hex(value),res)
    
    