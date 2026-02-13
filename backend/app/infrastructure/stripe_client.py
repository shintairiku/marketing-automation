# -*- coding: utf-8 -*-
"""
Stripe API client setup.
"""
import logging

import stripe

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_stripe_client():
    """Return configured Stripe module (singleton-style)."""
    if not settings.stripe_secret_key:
        raise ValueError("STRIPE_SECRET_KEY is not set")

    stripe.api_key = settings.stripe_secret_key
    return stripe
