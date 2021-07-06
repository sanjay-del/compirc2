
from inspect import Parameter
from iconservice import Address
from iconservice.base.exception import DatabaseException, IconScoreException 
from tbears.libs.scoretest.score_test_case import ScoreTestCase
from ..complete_irc2 import CompleteIRC2

class TestCase(ScoreTestCase):
    def setUp(self):
        super().setUp()
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
        self.score = self.get_score_instance(CompleteIRC2,self.test_account1, on_install_params=params )
        self.test_account3 = Address.from_string(f"hx{'12345'*8}")
        self.test_account4 = Address.from_string(f"hx{'12534'*8}")
        account_info = {
                self.test_account3: 10*10,
                self.test_account4: 10**12
                }
        self.initialize_accounts(account_info)
        
    def test_total_supply(self):
        self.assertEqual(self.initialSupply * 10 ** self.decimals, self.score.totalSupply())
        print(self.score.totalSupply())
            
    def test_mint(self):
        owner = self.test_account1
        value = 50
        print(f'Initially {self.score.totalSupply()}')
        self.set_msg(owner)
        extra = self.score.mint(value)
        print(f'final {self.score.totalSupply()}')    
    
    def test_mint_to(self):
        owner = self.test_account1
        value = 100
        to = self.test_account3
        print(f'Initially {self.score.balanceOf(to)}')
        self.set_msg(owner)
        self.score.mintTo(to,value)
        print(f'after minting by the owner {self.score.balanceOf(to)}')