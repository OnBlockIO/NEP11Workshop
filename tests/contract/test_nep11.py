import sys
import json
from PIL import Image
from typing import Dict
from pathlib import Path
from boa3_test.tests.boa_test import BoaTest
from boa3_test.tests.test_classes.testengine import TestEngine
from boa3.neo.smart_contract.VoidType import VoidType
from boa3.neo.cryptography import hash160
from boa3.constants import GAS_SCRIPT
from boa3.neo.vm.type.String import String
from boa3.boa3 import Boa3
from boa3.neo import to_script_hash, to_hex_str, from_hex_str
from boa3.builtin.type import UInt160
from boa3.builtin.interop.iterator import Iterator
from boa3_test.tests.test_classes.TestExecutionException import TestExecutionException
from boa3.neo.core.types.InteropInterface import InteropInterface


class NEP11Test(BoaTest):
    p = Path(__file__)
    NEP11_ROOT = str(p.parents[2])
    PRJ_ROOT = str(p.parents[3])

    CONTRACT_PATH_JSON = NEP11_ROOT + '/contracts/ascii-nft.manifest.json'
    CONTRACT_PATH_NEF = NEP11_ROOT + '/contracts/ascii-nft.nef'
    CONTRACT_PATH_PY = NEP11_ROOT + '/contracts/ascii-nft.py'

    # TODO add .env file and move test engine path there
    TEST_ENGINE_PATH = '../TestEngine/src/Neo.TestEngine/bin/Debug/net6.0/'
    OWNER_SCRIPT_HASH = UInt160(to_script_hash(
        b'NZcuGiwRu1QscpmCyxj5XwQBUf6sk7dJJN'))
    # OWNER_SCRIPT_HASH = UInt160(to_script_hash(b'NaCEUqriRmYeH9AKH11FvKGDJ1jWgBwAzi'))
    OTHER_ACCOUNT_1 = UInt160(to_script_hash(
        b'NiNmXL8FjEUEs1nfX9uHFBNaenxDHJtmuB'))
    OTHER_ACCOUNT_2 = bytes(range(20))
    TOKEN_META = bytes(
        '{ "name": "NEP11", "description": "Some description", "image": "{some image URI}", "tokenURI": "{some URI}" }', 'utf-8')
    TOKEN_LOCKED = bytes('lockedContent', 'utf-8')
    ROYALTIES = bytes(
        '[{"address": "NZcuGiwRu1QscpmCyxj5XwQBUf6sk7dJJN", "value": 2000}, {"address": "NiNmXL8FjEUEs1nfX9uHFBNaenxDHJtmuB", "value": 3000}]', 'utf-8')

    def build_contract(self, preprocess=False):
        print('contract path: ' + self.CONTRACT_PATH_PY)
        if preprocess:
            import os
            old = os.getcwd()
            os.chdir(self.GHOST_ROOT)
            file = self.GHOST_ROOT + '/compile.py'
            os.system(file)
            os.chdir(old)
        else:
            output, manifest = self.compile_and_save(self.CONTRACT_PATH_PY)
            self.CONTRACT = hash160(output)

    def deploy_contract(self, engine):
        # engine.add_contract(self.CONTRACT_PATH_NEF.replace('.py', '.nef'))
        engine.add_signer_account(self.OWNER_SCRIPT_HASH)
        result = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, '_deploy', self.OWNER_SCRIPT_HASH, False,
                                         signer_accounts=[
                                             self.OWNER_SCRIPT_HASH],
                                         expected_result_type=bool)

    def prepare_testengine(self, preprocess=False) -> TestEngine:
        # self.build_contract(preprocess)
        engine = TestEngine(self.TEST_ENGINE_PATH)
        engine.reset_engine()

        self.deploy_contract(engine)
        return engine

    def print_notif(self, notifications):
        print('\n=========================== NOTIFICATIONS START ===========================\n')
        for notif in notifications:
            print(f"{str(notif.name)}: {str(notif.arguments)}")
        print(
            '\n=========================== NOTIFICATIONS END ===========================\n')

    def test_nep11_symbol(self):
        engine = self.prepare_testengine()
        result = engine.run(self.CONTRACT_PATH_NEF,
                            'symbol', reset_engine=True)
        self.print_notif(engine.notifications)

        assert isinstance(result, str)
        assert result == 'ASCII'

    def test_nep11_decimals(self):
        engine = self.prepare_testengine()
        result = engine.run(self.CONTRACT_PATH_NEF,
                            'decimals', reset_engine=True)
        self.print_notif(engine.notifications)

        assert isinstance(result, int)
        assert result == 0

    def test_nep11_total_supply(self):
        engine = self.prepare_testengine()
        result = engine.run(self.CONTRACT_PATH_NEF,
                            'totalSupply', reset_engine=True)
        self.print_notif(engine.notifications)

        assert isinstance(result, int)
        assert result == 0

    def test_nep11_deploy(self):
        engine = self.prepare_testengine()
        # prepare_testengine already deploys the contract and verifies it's successfully deployed

        result = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, '_deploy', None, False,
                                         signer_accounts=[
                                             self.OWNER_SCRIPT_HASH],
                                         expected_result_type=bool)
        self.print_notif(engine.notifications)

    def test_nep11_authorize_2(self):
        engine = self.prepare_testengine()
        self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'setAuthorizedAddress',
                                self.OTHER_ACCOUNT_1, True,
                                signer_accounts=[self.OWNER_SCRIPT_HASH],
                                expected_result_type=bool)
        auth_events = engine.get_events('Authorized')

        # check if the event was triggered and the address was authorized
        self.assertEqual(0, auth_events[0].arguments[1])
        self.assertEqual(1, auth_events[0].arguments[2])

        # now deauthorize the address
        self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'setAuthorizedAddress',
                                self.OTHER_ACCOUNT_1, False,
                                signer_accounts=[self.OWNER_SCRIPT_HASH],
                                expected_result_type=bool)
        auth_events = engine.get_events('Authorized')
        # check if the event was triggered and the address was authorized
        self.assertEqual(0, auth_events[1].arguments[1])
        self.assertEqual(0, auth_events[1].arguments[2])

    def test_nep11_authorize(self):
        engine = self.prepare_testengine()
        self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'setAuthorizedAddress',
                                self.OTHER_ACCOUNT_1, True,
                                signer_accounts=[self.OWNER_SCRIPT_HASH],
                                expected_result_type=bool)
        auth_events = engine.get_events('Authorized')

        # check if the event was triggered and the address was authorized
        self.assertEqual(0, auth_events[0].arguments[1])
        self.assertEqual(1, auth_events[0].arguments[2])

        # now deauthorize the address
        self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'setAuthorizedAddress',
                                self.OTHER_ACCOUNT_1, False,
                                signer_accounts=[self.OWNER_SCRIPT_HASH],
                                expected_result_type=bool)
        auth_events = engine.get_events('Authorized')
        # check if the event was triggered and the address was authorized
        self.assertEqual(0, auth_events[1].arguments[1])
        self.assertEqual(0, auth_events[1].arguments[2])

    def test_nep11_pause(self):
        engine = self.prepare_testengine()
        engine.add_contract(self.CONTRACT_PATH_NEF.replace('.py', '.nef'))
        aux_path = self.get_contract_path(
            'test_native', 'auxiliary_contract.py')
        output, manifest = self.compile_and_save(
            self.CONTRACT_PATH_NEF.replace('.nef', '.py'))
        nep11_address = hash160(output)
        print(to_hex_str(nep11_address))
        output, manifest = self.compile_and_save(aux_path)
        aux_address = hash160(output)
        print(to_hex_str(aux_address))

        # add some gas for fees
        add_amount = 10 * 10 ** 8
        engine.add_gas(aux_address, add_amount)

        # pause contract
        fee = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'updatePause', True,
                                      signer_accounts=[self.OWNER_SCRIPT_HASH],
                                      expected_result_type=int)

        ascii_img = self.get_ascii_image()
        # should fail because contract is paused
        with self.assertRaises(TestExecutionException, msg=self.ASSERT_RESULTED_FALSE_MSG):
            token = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'mint',
                                            aux_address, self.TOKEN_META, self.TOKEN_LOCKED, self.ROYALTIES, ascii_img,
                                            signer_accounts=[aux_address],
                                            expected_result_type=bytes)

        # unpause contract
        fee = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'updatePause', False,
                                      signer_accounts=[self.OWNER_SCRIPT_HASH],
                                      expected_result_type=int)

        ascii_img = self.get_ascii_image()
        # mint
        token = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'mint',
                                        aux_address, self.TOKEN_META, self.TOKEN_LOCKED, self.ROYALTIES, ascii_img,
                                        signer_accounts=[aux_address],
                                        expected_result_type=bytes)
        self.print_notif(engine.notifications)

    def test_nep11_mint(self):
        engine = self.prepare_testengine()
        engine.add_contract(self.CONTRACT_PATH_NEF)
        aux_path = self.get_contract_path(
            'test_native', 'auxiliary_contract.py')
        output, manifest = self.compile_and_save(
            self.CONTRACT_PATH_NEF.replace('.nef', '.py'))
        nep11_address = hash160(output)
        print(to_hex_str(nep11_address))
        output, manifest = self.compile_and_save(aux_path)
        aux_address = hash160(output)
        print(to_hex_str(aux_address))

        # add some gas for fees
        add_amount = 10 * 10 ** 8
        engine.add_gas(aux_address, add_amount)

        ascii_img = self.get_ascii_image()
        # should succeed now that account has enough fees
        token = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'mint',
                                        aux_address, self.TOKEN_META, self.TOKEN_LOCKED, self.ROYALTIES, ascii_img,
                                        signer_accounts=[aux_address],
                                        expected_result_type=bytes)

        properties = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'properties', token, expected_result_type=bytes)
        img = json.loads(str(properties).replace("\'", "\""))["ascii"]
        royalties = self.run_smart_contract(
            engine, self.CONTRACT_PATH_NEF, 'getRoyalties', token, expected_result_type=bytes)
        with self.assertRaises(TestExecutionException, msg='An unhandled exception was thrown. Unable to parse metadata'):
            properties = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'properties',
                                                 bytes('thisisanonexistingtoken', 'utf-8'), expected_result_type=bytes)

        # check balances after
        # nep11_amount_after = self.run_smart_contract(engine, GAS_SCRIPT, 'balanceOf', nep11_address)
        # gas_aux_after = self.run_smart_contract(engine, GAS_SCRIPT, 'balanceOf', aux_address)
        # nep11_balance_after = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'balanceOf', aux_address)
        nep11_supply_after = self.run_smart_contract(
            engine, self.CONTRACT_PATH_NEF, 'totalSupply')
        self.assertEqual(1, nep11_supply_after)
        self.print_notif(engine.notifications)

    def test_nep11_transfer(self):
        engine = self.prepare_testengine()
        engine.add_contract(self.CONTRACT_PATH_NEF.replace('.py', '.nef'))
        aux_path = self.get_contract_path(
            'test_native', 'auxiliary_contract.py')
        output, manifest = self.compile_and_save(
            self.CONTRACT_PATH_NEF.replace('.nef', '.py'))
        nep11_address = hash160(output)
        print(to_hex_str(nep11_address))
        output, manifest = self.compile_and_save(aux_path)
        aux_address = hash160(output)
        print(to_hex_str(aux_address))

        # add some gas for fees
        add_amount = 10 * 10 ** 8
        engine.add_gas(aux_address, add_amount)

        ascii_img = self.get_ascii_image()
        # mint
        token = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'mint',
                                        aux_address, self.TOKEN_META, self.TOKEN_LOCKED, self.ROYALTIES, ascii_img,
                                        signer_accounts=[aux_address],
                                        expected_result_type=bytes)
        properties = self.run_smart_contract(
            engine, self.CONTRACT_PATH_NEF, 'properties', token)

        # check balances after
        nep11_amount_after = self.run_smart_contract(
            engine, GAS_SCRIPT, 'balanceOf', nep11_address)
        gas_aux_after = self.run_smart_contract(
            engine, GAS_SCRIPT, 'balanceOf', aux_address)
        nep11_balance_after = self.run_smart_contract(
            engine, self.CONTRACT_PATH_NEF, 'balanceOf', aux_address)
        nep11_supply_after = self.run_smart_contract(
            engine, self.CONTRACT_PATH_NEF, 'totalSupply')
        self.assertEqual(1, nep11_supply_after)

        # check owner before
        nep11_owner_of_before = self.run_smart_contract(
            engine, self.CONTRACT_PATH_NEF, 'ownerOf', token)

        # transfer
        result = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'transfer',
                                         self.OTHER_ACCOUNT_1, token, None,
                                         signer_accounts=[aux_address],
                                         expected_result_type=bool)
        self.assertEqual(True, result)

        # check owner after
        nep11_owner_of_after = self.run_smart_contract(
            engine, self.CONTRACT_PATH_NEF, 'ownerOf', token)
        self.assertEqual(nep11_owner_of_after, self.OTHER_ACCOUNT_1)

        # check balances after
        nep11_balance_after_transfer = self.run_smart_contract(
            engine, self.CONTRACT_PATH_NEF, 'balanceOf', aux_address)
        nep11_supply_after_transfer = self.run_smart_contract(
            engine, self.CONTRACT_PATH_NEF, 'totalSupply')
        self.assertEqual(0, nep11_balance_after_transfer)
        self.assertEqual(1, nep11_supply_after_transfer)

        # try to transfer non existing token id
        with self.assertRaises(TestExecutionException, msg=self.ASSERT_RESULTED_FALSE_MSG):
            result = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'transfer',
                                             self.OTHER_ACCOUNT_1, bytes(
                                                 'thisisanonexistingtoken', 'utf-8'), None,
                                             signer_accounts=[aux_address],
                                             expected_result_type=bool)

        self.print_notif(engine.notifications)

    def test_nep11_burn(self):
        engine = self.prepare_testengine()
        engine.add_contract(self.CONTRACT_PATH_NEF.replace('.py', '.nef'))
        aux_path = self.get_contract_path(
            'test_native', 'auxiliary_contract.py')
        output, manifest = self.compile_and_save(
            self.CONTRACT_PATH_NEF.replace('.nef', '.py'))
        nep11_address = hash160(output)
        output, manifest = self.compile_and_save(aux_path)
        aux_address = hash160(output)

        # add some gas for fees
        add_amount = 10 * 10 ** 8
        engine.add_gas(aux_address, add_amount)

        ascii_img = self.get_ascii_image()
        # mint
        token = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'mint',
                                        aux_address, self.TOKEN_META, self.TOKEN_LOCKED, self.ROYALTIES, ascii_img,
                                        signer_accounts=[aux_address],
                                        expected_result_type=bytes)

        # burn
        burn = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'burn', token,
                                       signer_accounts=[aux_address],
                                       expected_result_type=bool)

        # check balances after
        nep11_balance_after = self.run_smart_contract(
            engine, self.CONTRACT_PATH_NEF, 'balanceOf', aux_address)
        self.assertEqual(0, nep11_balance_after)
        nep11_supply_after = self.run_smart_contract(
            engine, self.CONTRACT_PATH_NEF, 'totalSupply')
        self.assertEqual(0, nep11_supply_after)
        self.print_notif(engine.notifications)

    def test_nep11_onNEP11Payment(self):
        engine = self.prepare_testengine()
        engine.add_contract(self.CONTRACT_PATH_NEF.replace('.py', '.nef'))
        aux_path = self.get_contract_path(
            'test_native', 'auxiliary_contract.py')
        output, manifest = self.compile_and_save(
            self.CONTRACT_PATH_NEF.replace('.nef', '.py'))
        nep11_address = hash160(output)
        print(to_hex_str(nep11_address))
        output, manifest = self.compile_and_save(aux_path)
        aux_address = hash160(output)
        print(to_hex_str(aux_address))

        # add some gas for fees
        add_amount = 10 * 10 ** 8
        engine.add_gas(self.OTHER_ACCOUNT_1, add_amount)

        ascii_img = self.get_ascii_image()
        # mint
        token = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'mint',
                                        self.OTHER_ACCOUNT_1, self.TOKEN_META, self.TOKEN_LOCKED, self.ROYALTIES, ascii_img,
                                        signer_accounts=[self.OTHER_ACCOUNT_1],
                                        expected_result_type=bytes)

        # the smart contract will abort if any address calls the NEP11 onPayment method
        with self.assertRaises(TestExecutionException, msg=self.ABORTED_CONTRACT_MSG):
            result = self.run_smart_contract(engine, self.CONTRACT_PATH_NEF, 'onNEP11Payment',
                                             self.OTHER_ACCOUNT_1, 1, token, None,
                                             signer_accounts=[
                                                 self.OTHER_ACCOUNT_1],
                                             expected_result_type=bool)

    def get_ascii_image(self):
        img = Image.open("/home/merl/Downloads/NEO_512_512.png")
        
        # resize the image
        width, height = img.size
        aspect_ratio = height / width
        new_width = 80
        new_height = aspect_ratio * new_width * 0.55
        img = img.resize((new_width, int(new_height)))
        
        # convert image to greyscale format
        new_img = img.convert('L')
        
        pixels = new_img.getdata()
        
        # replace each pixel with a character from array
        chars = ["B", "S", "#", "&", "@", "$", "%", "*", "!", ":", "."]
        new_pixels = [chars[pixel // 25] for pixel in pixels]
        new_pixels = ''.join(new_pixels)
        
        # split string of chars into multiple strings of length equal to new width and create a list
        new_pixels_count = len(new_pixels)
        ascii_image = [new_pixels[index:index + new_width] for index in range(0, new_pixels_count, new_width)]
        ascii_image = "\n".join(ascii_image)
        # print(ascii_image)
        with open("ascii_image.txt", "w") as f:
            f.write(ascii_image)
        return ascii_image
