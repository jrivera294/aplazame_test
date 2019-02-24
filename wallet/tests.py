from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from parameterized import parameterized

from wallet.models import User, Wallet, Transaction


class UserTests(APITestCase):
    fixtures = ['wallet/fixtures/initial_db.json']

    @parameterized.expand([
        (
                "customer",
                {
                    "username": "test_customer",
                    "email": "test_customer@example.com",
                    "groups": [
                        "customers"
                    ],
                    "first_name": "test",
                    "last_name": "customer"
                },
        ),
        (
                "merchant",
                {
                    "username": "test_merchant",
                    "email": "test_merchant@example.com",
                    "groups": [
                        "merchants"
                    ],
                    "first_name": "test",
                    "last_name": "merchant"
                },
        ),
    ])
    def test_create_account(self, _, data):
        url = reverse('user-list')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        db_user = User.objects.get(username=data["username"])
        self.assertEqual(db_user.email, data['email'])

        # TODO: Improve group check if many gropus per user is accepted
        db_user_groups = db_user.groups.all()
        self.assertEqual(len(db_user_groups), 1)
        self.assertEqual(db_user_groups[0].name, data['groups'][0])

    def test_create_customer_wallet(self):
        db_user = User.objects.get(username="test_customer_1")

        url = reverse('user-wallets', args=[db_user.id])
        data = {
            "user": db_user.id,
            "funds": 1000
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # TODO: Check DB

    def test_create_multiple_customer_wallets(self):
        db_user = User.objects.get(username="test_customer_1")

        url = reverse('user-wallets', args=[db_user.id])
        data = {
            "user": db_user.id,
            "funds": 1000
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response2 = self.client.post(url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        # TODO: Check DB

    def test_create_merchant_wallet(self):
        db_user = User.objects.get(username="test_merchant_1")

        url = reverse('user-wallets', args=[db_user.id])
        data = {
            "user": db_user.id,
            "funds": 1000
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # TODO: Check DB

    def test_create_multiple_merchant_wallets(self):
        db_user = User.objects.get(username="test_merchant_1")

        url = reverse('user-wallets', args=[db_user.id])
        data = {
            "user": db_user.id,
            "funds": 1000
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response2 = self.client.post(url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        # TODO: Check DB

    def test_get_user(self):
        db_user = User.objects.get(username="test_customer_with_wallet")

        # TODO: Mock wallet funds property, we dont want to test this method here
        Transaction(
            wallet_to=db_user.wallets.first().id,
            amount=100
        ).save()

        url = reverse('user-detail', args=[db_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_user = response.data
        self.assertEqual(len(response_user['wallets']), 1)
        self.assertEqual(response_user['wallets'][0]['funds'], 100)

        # TODO: Check DB


class WalletTests(APITestCase):
    fixtures = ['wallet/fixtures/initial_db.json']

    def test_get_empty_list_transactions(self):
        db_user = User.objects.get(username="test_customer_with_wallet")

        url = reverse('wallet-transactions', args=[db_user.wallets.first().id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_transactions(self):
        db_user = User.objects.get(username="test_customer_with_wallet")

        Transaction(
            wallet_to=db_user.wallets.first().id,
            amount=100
        ).save()

        url = reverse('wallet-transactions', args=[db_user.wallets.first().id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_add_funds(self):
        db_user_wallet = User.objects.get(username="test_customer_with_wallet").wallets.first()

        url = reverse('wallet-addFunds', args=[db_user_wallet.id])
        data = {
            "amount": 1000
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})
        self.assertEqual(db_user_wallet.funds, data["amount"])

    def test_charge(self):
        db_user_wallet = User.objects.get(username="test_customer_with_wallet").wallets.first()
        db_merchant_wallet = User.objects.get(username="test_merchant_with_wallet").wallets.first()

        initial_transaction = Transaction(
            wallet_to=db_user_wallet.id,
            amount=100
        )
        initial_transaction.save()

        url = reverse('wallet-charge', args=[db_user_wallet.id])
        data = {
            "amount": 50,
            "wallet_from": db_merchant_wallet.id,
            "invoice": "1"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})
        self.assertEqual(db_user_wallet.funds, initial_transaction.amount - data["amount"])
        self.assertEqual(db_merchant_wallet.funds, data["amount"])

    def test_double_charge(self):
        db_user_wallet = User.objects.get(username="test_customer_with_wallet").wallets.first()
        db_merchant_wallet = User.objects.get(username="test_merchant_with_wallet").wallets.first()

        initial_transaction = Transaction(
            wallet_to=db_user_wallet.id,
            amount=100
        )
        initial_transaction.save()

        url = reverse('wallet-charge', args=[db_user_wallet.id])
        data = {
            "amount": 50,
            "wallet_from": db_merchant_wallet.id,
            "invoice": "1"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})

        with self.assertRaises(IntegrityError):
            self.client.post(url, data, format='json')

    def test_insufficient_funds(self):
        db_user_wallet = User.objects.get(username="test_customer_with_wallet").wallets.first()
        db_merchant_wallet = User.objects.get(username="test_merchant_with_wallet").wallets.first()

        url = reverse('wallet-charge', args=[db_user_wallet.id])
        data = {
            "amount": 50,
            "wallet_from": db_merchant_wallet.id,
            "invoice": "1"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(response.data, {
            'amount': 'Insufficient funds'
        })
