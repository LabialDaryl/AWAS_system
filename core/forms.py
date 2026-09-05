"""
Core forms module.
Reuses MembershipRequestForm from accounts for water connection requests.
"""
from accounts.forms import MembershipRequestForm

# Alias for backwards compatibility with core views and templates
ConnectionRequestForm = MembershipRequestForm

