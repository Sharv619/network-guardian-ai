"""
Stripe Billing Integration for Network Guardian AI.

Handles:
- Subscription management (free, pro, enterprise tiers)
- Payment processing
- Webhooks for subscription events
- Usage-based billing
"""

from datetime import datetime
from typing import Any

import stripe
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class SubscriptionTier:
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    TIERS = {
        FREE: {
            "name": "Free",
            "price_monthly": 0,
            "price_yearly": 0,
            "requests_per_day": 100,
            "requests_per_minute": 10,
            "features": ["basic_dns_analysis", "domain_history"],
        },
        PRO: {
            "name": "Pro",
            "price_monthly": 29,
            "price_yearly": 290,
            "requests_per_day": 10000,
            "requests_per_minute": 100,
            "features": ["basic_dns_analysis", "domain_history", "ml_heuristics", "blocklists"],
        },
        ENTERPRISE: {
            "name": "Enterprise",
            "price_monthly": 99,
            "price_yearly": 990,
            "requests_per_day": -1,
            "requests_per_minute": -1,
            "features": [
                "basic_dns_analysis",
                "domain_history",
                "ml_heuristics",
                "blocklists",
                "api_access",
                "priority_support",
                "custom_integrations",
            ],
        },
    }

    @classmethod
    def get_tier_config(cls, tier: str) -> dict[str, Any]:
        return cls.TIERS.get(tier, cls.TIERS[cls.FREE])

    @classmethod
    def is_valid_tier(cls, tier: str) -> bool:
        return tier in cls.TIERS


class StripeConfig:
    def __init__(self) -> None:
        stripe.api_key = settings.STRIPE_API_KEY or "sk_test_placeholder"
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET or ""
        self.price_ids = {
            SubscriptionTier.PRO: settings.STRIPE_PRO_PRICE_ID or "price_pro_placeholder",
            SubscriptionTier.ENTERPRISE: settings.STRIPE_ENTERPRISE_PRICE_ID
            or "price_enterprise_placeholder",
        }


class BillingService:
    def __init__(self) -> None:
        self.stripe = stripe
        self.config = StripeConfig()

    def create_customer(
        self, email: str, name: str, tenant_id: int, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a new Stripe customer."""
        try:
            customer = self.stripe.Customer.create(
                email=email,
                name=name,
                metadata={
                    "tenant_id": str(tenant_id),
                    **(metadata or {}),
                },
            )
            logger.info(f"Created Stripe customer: {customer.id} for tenant {tenant_id}")
            return {
                "customer_id": customer.id,
                "email": customer.email,
                "name": customer.name,
            }
        except Exception as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        """Get Stripe customer details."""
        try:
            customer = self.stripe.Customer.retrieve(customer_id)
            return {
                "customer_id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "balance": customer.balance,
            }
        except Exception as e:
            logger.error(f"Failed to get Stripe customer: {e}")
            return None

    def create_checkout_session(
        self,
        customer_id: str,
        tier: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        """Create a Stripe Checkout session for subscription upgrade."""
        try:
            price_id = self.config.price_ids.get(tier)
            if not price_id:
                raise ValueError(f"No price configured for tier: {tier}")

            session = self.stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "tier": tier,
                },
            )
            logger.info(f"Created checkout session: {session.id} for customer {customer_id}")
            return {
                "session_id": session.id,
                "url": session.url,
            }
        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise

    def create_portal_session(self, customer_id: str, return_url: str) -> dict[str, Any]:
        """Create a Stripe Customer Portal session."""
        try:
            session = self.stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return {
                "session_id": session.id,
                "url": session.url,
            }
        except Exception as e:
            logger.error(f"Failed to create portal session: {e}")
            raise

    def get_subscription(self, subscription_id: str) -> dict[str, Any] | None:
        """Get subscription details."""
        try:
            sub = self.stripe.Subscription.retrieve(subscription_id)
            return {
                "subscription_id": sub.id,
                "customer_id": sub.customer,
                "status": sub.status,
                "tier": sub.metadata.get("tier", SubscriptionTier.FREE),
                "current_period_end": datetime.fromtimestamp(sub.current_period_end),
                "cancel_at_period_end": sub.cancel_at_period_end,
            }
        except Exception as e:
            logger.error(f"Failed to get subscription: {e}")
            return None

    def cancel_subscription(
        self, subscription_id: str, immediately: bool = False
    ) -> dict[str, Any]:
        """Cancel a subscription."""
        try:
            if immediately:
                sub = self.stripe.Subscription.delete(subscription_id)
            else:
                sub = self.stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
            logger.info(f"Cancelled subscription: {subscription_id}, immediately={immediately}")
            return {
                "subscription_id": sub.id,
                "status": sub.status,
                "cancel_at_period_end": sub.cancel_at_period_end,
            }
        except Exception as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise

    def update_subscription_tier(self, subscription_id: str, new_tier: str) -> dict[str, Any]:
        """Update subscription tier."""
        try:
            price_id = self.config.price_ids.get(new_tier)
            if not price_id:
                raise ValueError(f"No price configured for tier: {new_tier}")

            sub = self.stripe.Subscription.modify(
                subscription_id,
                items=[
                    {
                        "price": price_id,
                    }
                ],
                metadata={"tier": new_tier},
            )
            logger.info(f"Updated subscription {subscription_id} to tier {new_tier}")
            return {
                "subscription_id": sub.id,
                "status": sub.status,
                "tier": new_tier,
            }
        except Exception as e:
            logger.error(f"Failed to update subscription tier: {e}")
            raise

    def get_usage_for_tenant(
        self, tenant_id: int, period_start: datetime, period_end: datetime
    ) -> dict[str, Any]:
        """Get usage statistics for a tenant."""
        try:
            from backend.db.repository import DomainRepository

            repo = DomainRepository()
            stats = repo.get_domain_stats(tenant_id)

            tier_config = SubscriptionTier.get_tier_config(
                stats.get("subscription_tier", SubscriptionTier.FREE)
            )
            daily_limit = tier_config["requests_per_day"]

            return {
                "tenant_id": tenant_id,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "domains_analyzed": stats.get("total_analyzed", 0),
                "threats_detected": stats.get("threats_detected", 0),
                "daily_limit": daily_limit,
                "unlimited": daily_limit == -1,
            }
        except Exception as e:
            logger.error(f"Failed to get usage for tenant {tenant_id}: {e}")
            return {
                "tenant_id": tenant_id,
                "error": str(e),
            }

    @staticmethod
    def construct_webhook_event(payload: bytes, sig: str, webhook_secret: str) -> dict[str, Any]:
        """Construct a webhook event from payload and signature."""
        try:
            event = stripe.Event.construct_from(
                {"id": "evt_placeholder", "data": {"object": {}}},
                stripe.api_key,
                raises=True,
            )
            return {"type": event.type, "data": event.data.object}
        except Exception:
            if webhook_secret:
                return stripe.Webhook.construct_event(payload, sig, webhook_secret)
            return {"type": "unknown", "data": {}}

    def handle_webhook_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming webhook events."""
        event_type = event.get("type", "")
        data = event.get("data", {}).get("object", {})

        handlers = {
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_payment_failed,
        }

        handler = handlers.get(event_type)
        if handler:
            return handler(data)

        logger.info(f"Unhandled webhook event: {event_type}")
        return {"handled": False, "event": event_type}

    def _handle_subscription_created(self, data: dict[str, Any]) -> dict[str, Any]:
        tenant_id = data.get("metadata", {}).get("tenant_id")
        tier = data.get("metadata", {}).get("tier", SubscriptionTier.FREE)

        if tenant_id:
            logger.info(f"Subscription created for tenant {tenant_id}, tier: {tier}")
            from backend.db.repository import TenantRepository

            repo = TenantRepository()
            repo.update_subscription_tier(int(tenant_id), tier)

        return {"handled": True, "action": "subscription_created", "tenant_id": tenant_id}

    def _handle_subscription_updated(self, data: dict[str, Any]) -> dict[str, Any]:
        tenant_id = data.get("metadata", {}).get("tenant_id")
        tier = data.get("metadata", {}).get("tier", SubscriptionTier.FREE)

        if tenant_id:
            logger.info(f"Subscription updated for tenant {tenant_id}, tier: {tier}")
            from backend.db.repository import TenantRepository

            repo = TenantRepository()
            repo.update_subscription_tier(int(tenant_id), tier)

        return {"handled": True, "action": "subscription_updated", "tenant_id": tenant_id}

    def _handle_subscription_deleted(self, data: dict[str, Any]) -> dict[str, Any]:
        tenant_id = data.get("metadata", {}).get("tenant_id")

        if tenant_id:
            logger.info(f"Subscription deleted for tenant {tenant_id}, downgrading to free")
            from backend.db.repository import TenantRepository

            repo = TenantRepository()
            repo.update_subscription_tier(int(tenant_id), SubscriptionTier.FREE)

        return {"handled": True, "action": "subscription_deleted", "tenant_id": tenant_id}

    def _handle_invoice_paid(self, data: dict[str, Any]) -> dict[str, Any]:
        customer_id = data.get("customer")
        logger.info(f"Invoice paid for customer: {customer_id}")
        return {"handled": True, "action": "invoice_paid", "customer_id": customer_id}

    def _handle_payment_failed(self, data: dict[str, Any]) -> dict[str, Any]:
        customer_id = data.get("customer")
        logger.warning(f"Payment failed for customer: {customer_id}")
        return {"handled": True, "action": "payment_failed", "customer_id": customer_id}


billing_service = BillingService()
