from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from wallet.serializers import UserSerializer, WalletSerializer, TransactionSerializer
from wallet.models import Wallet, User, Transaction


class UserViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=True, methods=['POST'])
    def wallets(self, request, pk=None):
        """
        post: Create a wallet linked to the given user.
        Customers users could have multiple wallets.
        Merchants users can only have one wallet.
        """
        user = self.get_object()

        if user.is_in_group('merchants') and len(user.wallets.all()) > 0:
            return Response({
                "user": "Merchants can only have one wallet"
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            wallet = Wallet(user=user)
            user.wallets.add(wallet, bulk=False)
            return Response(WalletSerializer(wallet).data, status=status.HTTP_201_CREATED)


class WalletViewSet(viewsets.GenericViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

    @action(detail=True, methods=['GET'])
    def transactions(self, request, pk=None):
        """
        Return a list of all transactions of the given wallet
        """
        transactions = Transaction.objects.filter(wallet_to=pk)
        return Response(TransactionSerializer(transactions, many=True).data)

    @action(detail=True, methods=['POST'])
    @Transaction.atomic_transaction
    def addFunds(self, request, pk=None):
        """
        Add funds to the given wallet
        """
        amount = request.data.get('amount')

        if amount and amount <= 0:
            return Response({
                'amount': 'Must be a decimal greater than 0'
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            transaction = Transaction(
                amount=amount,
                wallet_to=pk
            )
            transaction.save()
            return Response({}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    @Transaction.atomic_transaction
    def charge(self, request, pk=None):
        """
        Charge a given amount to the specified wallet.

        Invoice body parameter is used to avoid double charges,
        it's persisted only when the transaction is accepted.
        """
        # TODO: Validate that wallet_from exists
        # TODO: Catch IntegrityErrors and throw a proper REST response

        amount = request.data.get('amount')
        invoice = request.data.get('invoice')
        wallet_from = request.data.get('wallet_from')

        if amount <= 0:
            return Response({
                'amount': 'Must be a decimal greater than 0'
            }, status=status.HTTP_400_BAD_REQUEST)
        elif not invoice:
            return Response({
                'invoice': 'Required'
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Check funds
            if Transaction.get_wallet_funds(pk) >= amount:
                accepted = True
                comment = None
                response = Response({}, status=status.HTTP_200_OK)
            else:
                accepted = False
                comment = 'Insufficient funds'
                invoice = None  # TODO: Do a better constraint or validation
                response = Response({
                    'amount': comment
                }, status=status.HTTP_402_PAYMENT_REQUIRED)

            # Make debit transaction
            Transaction(
                amount=amount * -1,
                wallet_to=pk,
                wallet_from=wallet_from,
                invoice=invoice,
                accepted=accepted,
                comment=comment
            ).save()

            # Make credit transaction
            Transaction(
                amount=amount,
                wallet_to=wallet_from,
                wallet_from=pk,
                invoice=invoice,
                accepted=accepted,
                comment=comment
            ).save()

            return response
