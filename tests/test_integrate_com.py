from inspect import signature
import json
import os
from typing import Union, List

from iconsdk.builder.call_builder import CallBuilder
from iconsdk.builder.transaction_builder import TransactionBuilder, DeployTransactionBuilder, CallTransactionBuilder
from iconsdk.libs.in_memory_zip import gen_deploy_data_content
from iconsdk.signed_transaction import SignedTransaction
from iconsdk.wallet.wallet import KeyWallet
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

class score_test_utlis(IconIntegrateTestBase):
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
        