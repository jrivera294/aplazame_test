from django.contrib.auth.models import Group
from rest_framework import serializers

from wallet.models import Wallet, Transaction, User


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('id', 'funds', 'updated_at', 'created_at')


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        required=False,
        queryset=Group.objects.all()
    )
    wallets = WalletSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups', 'first_name', 'last_name', 'wallets')


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('id', 'wallet_to', 'wallet_from', 'amount', 'accepted', 'comment', 'created_at', 'invoice')
