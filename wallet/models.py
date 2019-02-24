import uuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.db.transaction import atomic


class User(AbstractUser):

    def is_in_group(self, group_name):
        return self.groups.filter(name=group_name).exists()


class Transaction(models.Model):
    wallet_to = models.UUIDField(null=False)
    wallet_from = models.UUIDField(null=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2, null=False)
    accepted = models.BooleanField(default=True)
    comment = models.CharField(max_length=128, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    invoice = models.CharField(max_length=30, null=True)

    @staticmethod
    def get_wallet_funds(wallet):
        funds = Transaction.objects.filter(accepted=True, wallet_to=wallet).aggregate(funds=Sum('amount'))['funds']
        return funds if funds else 0

    @staticmethod
    def atomic_transaction(function):
        def wrap(request, *args, **kwargs):
            pk = kwargs.get('pk')
            with atomic():
                # All matched entries will be locked until the end of the transaction block,
                # meaning that other transactions will be prevented from changing or acquiring locks on them.
                try:
                    last_transaction = Transaction.objects.select_for_update().filter(wallet_to=pk).latest('id')
                except Transaction.DoesNotExist:
                    pass

                return function(request, *args, **kwargs)

        wrap.__doc__ = function.__doc__
        wrap.__name__ = function.__name__
        return wrap

    class Meta:
        unique_together = (('invoice', 'wallet_to'),)


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, related_name="wallets", on_delete=models.DO_NOTHING)
    # funds = models.DecimalField(max_digits=8, decimal_places=2, null=False, default=0)
    updated_at = models.DateTimeField(db_index=True, auto_now=True, null=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False)

    @property
    def funds(self):
        """Calculate the funds of the selected wallet

        Currently using On-demand, without cache policy.
        It could be a controlled Up-to-date method, using a cache policy with a reasonable expiry time

        :return:
        """
        return Transaction.get_wallet_funds(self.id)
