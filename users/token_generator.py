from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six


class account_activation_token(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (six.text_type(user.is_active)+six.text_type(user.pk) + six.text_type(timestamp))


account_activation_token = account_activation_token()
