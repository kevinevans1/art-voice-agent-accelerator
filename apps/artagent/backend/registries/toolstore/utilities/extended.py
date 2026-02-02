"""
Additional Utilities Tools
==========================

Extended tools for utilities agents - billing, service, usage.
These complement the core tools in utilities.py

Tools added here are referenced by agent YAML but were missing implementations:
- Billing: get_bill_history, explain_charges, get_payment_history, setup_autopay,
           apply_credit, request_bill_review, check_eligible_credits, 
           update_billing_address, check_assistance_programs, enroll_budget_billing
- Account: get_payment_status, get_service_address, verify_customer_identity
- Outage: get_restoration_eta, get_outage_map, subscribe_outage_updates,
          get_emergency_contacts, check_outage_credits, request_outage_credit, 
          report_gas_leak
- Service: start_new_service, stop_service, schedule_meter_read,
           check_available_dates, schedule_appointment, reschedule_appointment,
           cancel_appointment, verify_service_address, check_service_availability,
           get_deposit_requirement, update_contact_info, add_authorized_user,
           enroll_paperless, enroll_autopay
- Usage: get_usage_comparison, get_usage_breakdown, compare_to_neighbors,
         get_meter_info, submit_meter_read, request_meter_test, explain_meter_reading,
         calculate_appliance_cost, get_rebate_programs, schedule_energy_audit,
         enroll_time_of_use, enroll_demand_response, check_solar_eligibility, 
         get_rate_schedule
- Escalation: escalate_human, schedule_callback

Note: Omnichannel tools (check_queue_status, offer_channel_switch, execute_channel_handoff)
are now registered in channel_handoff.py which is imported first in registry.py.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.artagent.backend.registries.toolstore.registry import register_tool
from utils.ml_logging import get_logger

logger = get_logger("tools.utilities.extended")


# ═══════════════════════════════════════════════════════════════════════════════
# IDENTITY & ACCOUNT TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

verify_customer_identity_schema: dict[str, Any] = {
    "name": "verify_customer_identity",
    "description": "Verify customer identity using account number and verification method.",
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "verification_method": {
                "type": "string",
                "enum": ["last_4_ssn", "phone", "address", "security_question"],
            },
            "verification_value": {"type": "string"},
        },
        "required": ["account_number"],
    },
}


async def verify_customer_identity_executor(**kwargs: Any) -> dict[str, Any]:
    """Verify customer identity."""
    return {
        "success": True,
        "verified": True,
        "customer_name": "John Smith",
        "account_status": "Active",
        "verification_method": kwargs.get("verification_method", "phone"),
    }


get_account_info_schema: dict[str, Any] = {
    "name": "get_account_info",
    "description": "Get customer account information.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def get_account_info_executor(**kwargs: Any) -> dict[str, Any]:
    """Get account information."""
    return {
        "success": True,
        "account_number": kwargs.get("account_number", "12345"),
        "customer_name": "John Smith",
        "service_address": "123 Main St, Springfield, IL 62701",
        "mailing_address": "123 Main St, Springfield, IL 62701",
        "account_status": "Active",
        "service_type": "Electric & Gas",
        "account_since": "2018-03-15",
        "autopay_enrolled": True,
        "paperless_enrolled": True,
    }


get_service_address_schema: dict[str, Any] = {
    "name": "get_service_address",
    "description": "Get the service address for a customer account.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def get_service_address_executor(**kwargs: Any) -> dict[str, Any]:
    """Get service address."""
    return {
        "success": True,
        "service_address": "123 Main St, Springfield, IL 62701",
        "meter_number": "MTR-" + str(random.randint(100000, 999999)),
        "service_type": "Electric & Gas",
    }


get_payment_status_schema: dict[str, Any] = {
    "name": "get_payment_status",
    "description": "Check the payment status for a customer account.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def get_payment_status_executor(**kwargs: Any) -> dict[str, Any]:
    """Get payment status."""
    return {
        "success": True,
        "current_balance": round(random.uniform(50, 200), 2),
        "past_due_amount": 0,
        "payment_status": "Current",
        "last_payment": {
            "amount": round(random.uniform(100, 200), 2),
            "date": (datetime.now(UTC) - timedelta(days=15)).strftime("%B %d, %Y"),
            "method": "Autopay",
        },
        "next_due_date": (datetime.now(UTC) + timedelta(days=15)).strftime("%B %d, %Y"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING EXTENDED TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

get_bill_history_schema: dict[str, Any] = {
    "name": "get_bill_history",
    "description": "Get billing history for the account.",
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "months": {"type": "integer", "description": "Number of months of history"},
        },
        "required": [],
    },
}


async def get_bill_history_executor(**kwargs: Any) -> dict[str, Any]:
    """Get billing history."""
    months = kwargs.get("months", 6)
    history = []
    for i in range(months):
        bill_date = datetime.now(UTC) - timedelta(days=30 * i)
        history.append({
            "bill_date": bill_date.strftime("%B %Y"),
            "amount": round(random.uniform(80, 200), 2),
            "paid": True,
            "payment_date": (bill_date + timedelta(days=10)).strftime("%B %d, %Y"),
        })
    return {"success": True, "history": history}


explain_charges_schema: dict[str, Any] = {
    "name": "explain_charges",
    "description": "Explain specific charges on the bill.",
    "parameters": {
        "type": "object",
        "properties": {
            "charge_type": {"type": "string", "description": "Type of charge to explain"},
        },
        "required": [],
    },
}


async def explain_charges_executor(**kwargs: Any) -> dict[str, Any]:
    """Explain charges."""
    charge_type = kwargs.get("charge_type", "distribution")
    explanations = {
        "distribution": "The distribution charge covers the cost of maintaining the power lines, transformers, and other infrastructure that delivers electricity to your home.",
        "generation": "The generation charge covers the cost of producing electricity at power plants.",
        "transmission": "The transmission charge covers the cost of moving electricity from power plants to local distribution systems.",
        "fuel": "The fuel adjustment reflects changes in the cost of fuel used to generate electricity.",
    }
    return {
        "success": True,
        "charge_type": charge_type,
        "explanation": explanations.get(charge_type, "This charge covers utility service costs."),
    }


get_payment_history_schema: dict[str, Any] = {
    "name": "get_payment_history",
    "description": "Get payment history for the account.",
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "months": {"type": "integer"},
        },
        "required": [],
    },
}


async def get_payment_history_executor(**kwargs: Any) -> dict[str, Any]:
    """Get payment history."""
    months = kwargs.get("months", 6)
    history = []
    for i in range(months):
        pay_date = datetime.now(UTC) - timedelta(days=30 * i + 10)
        history.append({
            "date": pay_date.strftime("%B %d, %Y"),
            "amount": round(random.uniform(80, 200), 2),
            "method": random.choice(["Autopay", "Credit Card", "Bank Transfer"]),
            "confirmation": f"PAY{random.randint(100000, 999999)}",
        })
    return {"success": True, "payments": history}


setup_autopay_schema: dict[str, Any] = {
    "name": "setup_autopay",
    "description": "Set up automatic payment for the account.",
    "parameters": {
        "type": "object",
        "properties": {
            "payment_method": {"type": "string", "enum": ["bank_account", "credit_card", "debit_card"]},
        },
        "required": ["payment_method"],
    },
}


async def setup_autopay_executor(**kwargs: Any) -> dict[str, Any]:
    """Set up autopay."""
    return {
        "success": True,
        "enrolled": True,
        "payment_method": kwargs.get("payment_method", "bank_account"),
        "start_date": (datetime.now(UTC) + timedelta(days=30)).strftime("%B %d, %Y"),
        "message": "Autopay enrolled successfully. Your first automatic payment will be on your next due date.",
    }


apply_credit_schema: dict[str, Any] = {
    "name": "apply_credit",
    "description": "Apply a credit to the customer's account.",
    "parameters": {
        "type": "object",
        "properties": {
            "credit_type": {"type": "string"},
            "amount": {"type": "number"},
            "reason": {"type": "string"},
        },
        "required": ["credit_type"],
    },
}


async def apply_credit_executor(**kwargs: Any) -> dict[str, Any]:
    """Apply credit to account."""
    amount = kwargs.get("amount", 25.00)
    return {
        "success": True,
        "credit_applied": amount,
        "credit_type": kwargs.get("credit_type", "goodwill"),
        "new_balance": round(random.uniform(50, 150) - amount, 2),
        "confirmation": f"CRD{random.randint(100000, 999999)}",
    }


request_bill_review_schema: dict[str, Any] = {
    "name": "request_bill_review",
    "description": "Request a review of a bill for potential errors.",
    "parameters": {
        "type": "object",
        "properties": {
            "bill_date": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["reason"],
    },
}


async def request_bill_review_executor(**kwargs: Any) -> dict[str, Any]:
    """Request bill review."""
    return {
        "success": True,
        "review_id": f"REV{random.randint(100000, 999999)}",
        "estimated_completion": "3-5 business days",
        "message": "Your bill review request has been submitted. We'll contact you with the results.",
    }


check_eligible_credits_schema: dict[str, Any] = {
    "name": "check_eligible_credits",
    "description": "Check what credits the customer may be eligible for.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def check_eligible_credits_executor(**kwargs: Any) -> dict[str, Any]:
    """Check eligible credits."""
    return {
        "success": True,
        "eligible_credits": [
            {"type": "Outage Credit", "amount": 15.00, "reason": "Extended outage last month"},
            {"type": "Paperless Discount", "amount": 2.00, "reason": "Monthly paperless billing discount"},
        ],
        "total_available": 17.00,
    }


update_billing_address_schema: dict[str, Any] = {
    "name": "update_billing_address",
    "description": "Update the mailing/billing address for the account.",
    "parameters": {
        "type": "object",
        "properties": {"new_address": {"type": "string"}},
        "required": ["new_address"],
    },
}


async def update_billing_address_executor(**kwargs: Any) -> dict[str, Any]:
    """Update billing address."""
    return {
        "success": True,
        "new_address": kwargs.get("new_address"),
        "effective_date": "Immediately",
        "message": "Your billing address has been updated.",
    }


check_assistance_programs_schema: dict[str, Any] = {
    "name": "check_assistance_programs",
    "description": "Check available assistance programs for the customer.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def check_assistance_programs_executor(**kwargs: Any) -> dict[str, Any]:
    """Check assistance programs."""
    return {
        "success": True,
        "programs": [
            {"name": "LIHEAP", "description": "Low Income Home Energy Assistance Program", "eligible": True},
            {"name": "Budget Billing", "description": "Spread annual costs evenly over 12 months", "eligible": True},
            {"name": "Medical Baseline", "description": "Additional allowance for medical equipment", "eligible": False},
        ],
    }


enroll_budget_billing_schema: dict[str, Any] = {
    "name": "enroll_budget_billing",
    "description": "Enroll in budget billing to spread costs evenly.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def enroll_budget_billing_executor(**kwargs: Any) -> dict[str, Any]:
    """Enroll in budget billing."""
    monthly = round(random.uniform(100, 180), 2)
    return {
        "success": True,
        "enrolled": True,
        "monthly_amount": monthly,
        "start_date": (datetime.now(UTC) + timedelta(days=30)).strftime("%B %Y"),
        "message": f"Enrolled in Budget Billing at ${monthly}/month based on your 12-month average.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# OUTAGE EXTENDED TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

get_restoration_eta_schema: dict[str, Any] = {
    "name": "get_restoration_eta",
    "description": "Get the estimated restoration time for an active outage.",
    "parameters": {
        "type": "object",
        "properties": {
            "service_address": {"type": "string"},
            "outage_id": {"type": "string"},
        },
        "required": [],
    },
}


async def get_restoration_eta_executor(**kwargs: Any) -> dict[str, Any]:
    """Get restoration ETA."""
    hours = random.randint(1, 6)
    return {
        "success": True,
        "estimated_restoration": (datetime.now(UTC) + timedelta(hours=hours)).strftime("%I:%M %p"),
        "crew_status": "On site",
        "customers_affected": random.randint(50, 500),
        "cause": random.choice(["Tree contact", "Equipment failure", "Storm damage"]),
    }


get_outage_map_schema: dict[str, Any] = {
    "name": "get_outage_map",
    "description": "Get a link to the outage map.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}


async def get_outage_map_executor(**kwargs: Any) -> dict[str, Any]:
    """Get outage map link."""
    return {
        "success": True,
        "map_url": "https://example.com/outage-map",
        "current_outages": random.randint(1, 20),
        "customers_affected_total": random.randint(500, 5000),
    }


subscribe_outage_updates_schema: dict[str, Any] = {
    "name": "subscribe_outage_updates",
    "description": "Subscribe to updates for an outage.",
    "parameters": {
        "type": "object",
        "properties": {
            "notification_method": {"type": "string", "enum": ["sms", "email", "both"]},
        },
        "required": [],
    },
}


async def subscribe_outage_updates_executor(**kwargs: Any) -> dict[str, Any]:
    """Subscribe to outage updates."""
    return {
        "success": True,
        "subscribed": True,
        "method": kwargs.get("notification_method", "sms"),
        "message": "You'll receive updates as the situation changes.",
    }


get_emergency_contacts_schema: dict[str, Any] = {
    "name": "get_emergency_contacts",
    "description": "Get emergency contact numbers.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}


async def get_emergency_contacts_executor(**kwargs: Any) -> dict[str, Any]:
    """Get emergency contacts."""
    return {
        "success": True,
        "contacts": [
            {"type": "Power Outage", "number": "1-800-555-0100"},
            {"type": "Gas Emergency", "number": "1-800-555-0200"},
            {"type": "Downed Wire", "number": "911"},
        ],
    }


check_outage_credits_schema: dict[str, Any] = {
    "name": "check_outage_credits",
    "description": "Check if customer is eligible for outage credits.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def check_outage_credits_executor(**kwargs: Any) -> dict[str, Any]:
    """Check outage credits."""
    return {
        "success": True,
        "eligible": True,
        "outage_hours": 8,
        "credit_amount": 25.00,
        "auto_applied": True,
        "message": "Credit will appear on your next bill.",
    }


request_outage_credit_schema: dict[str, Any] = {
    "name": "request_outage_credit",
    "description": "Request a credit for an outage.",
    "parameters": {
        "type": "object",
        "properties": {
            "outage_date": {"type": "string"},
            "hours_without_power": {"type": "number"},
        },
        "required": [],
    },
}


async def request_outage_credit_executor(**kwargs: Any) -> dict[str, Any]:
    """Request outage credit."""
    hours = kwargs.get("hours_without_power", 4)
    credit = 5.00 * (hours // 4)
    return {
        "success": True,
        "request_id": f"OCR{random.randint(100000, 999999)}",
        "estimated_credit": credit,
        "status": "Under review",
    }


report_gas_leak_schema: dict[str, Any] = {
    "name": "report_gas_leak",
    "description": "EMERGENCY: Report a suspected gas leak.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {"type": "string"},
            "smell_description": {"type": "string"},
        },
        "required": ["location"],
    },
}


async def report_gas_leak_executor(**kwargs: Any) -> dict[str, Any]:
    """Report gas leak emergency."""
    return {
        "success": True,
        "emergency_ticket": f"GAS{random.randint(10000, 99999)}",
        "priority": "CRITICAL",
        "crew_dispatched": True,
        "estimated_arrival": "10-15 minutes",
        "safety_message": "Leave the area immediately. Do not use any electrical switches or open flames. Call 911 if you feel ill.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE EXTENDED TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

start_new_service_schema: dict[str, Any] = {
    "name": "start_new_service",
    "description": "Start new utility service at an address.",
    "parameters": {
        "type": "object",
        "properties": {
            "service_address": {"type": "string"},
            "start_date": {"type": "string"},
            "service_types": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["service_address", "start_date"],
    },
}


async def start_new_service_executor(**kwargs: Any) -> dict[str, Any]:
    """Start new service."""
    return {
        "success": True,
        "order_number": f"NEW{random.randint(100000, 999999)}",
        "service_address": kwargs.get("service_address"),
        "start_date": kwargs.get("start_date"),
        "deposit_required": random.choice([True, False]),
        "deposit_amount": 150.00 if random.random() > 0.5 else 0,
        "message": "Your new service request has been submitted.",
    }


stop_service_schema: dict[str, Any] = {
    "name": "stop_service",
    "description": "Stop utility service at an address.",
    "parameters": {
        "type": "object",
        "properties": {
            "service_address": {"type": "string"},
            "stop_date": {"type": "string"},
            "forwarding_address": {"type": "string"},
        },
        "required": ["stop_date"],
    },
}


async def stop_service_executor(**kwargs: Any) -> dict[str, Any]:
    """Stop service."""
    return {
        "success": True,
        "order_number": f"STP{random.randint(100000, 999999)}",
        "stop_date": kwargs.get("stop_date"),
        "final_bill_date": (datetime.now(UTC) + timedelta(days=7)).strftime("%B %d, %Y"),
        "message": "Service stop scheduled. Final bill will be sent to your forwarding address.",
    }


schedule_meter_read_schema: dict[str, Any] = {
    "name": "schedule_meter_read",
    "description": "Schedule a meter read for the account.",
    "parameters": {
        "type": "object",
        "properties": {"preferred_date": {"type": "string"}},
        "required": [],
    },
}


async def schedule_meter_read_executor(**kwargs: Any) -> dict[str, Any]:
    """Schedule meter read."""
    return {
        "success": True,
        "scheduled_date": kwargs.get("preferred_date", (datetime.now(UTC) + timedelta(days=3)).strftime("%B %d, %Y")),
        "time_window": "8 AM - 12 PM",
        "confirmation": f"MR{random.randint(100000, 999999)}",
    }


check_available_dates_schema: dict[str, Any] = {
    "name": "check_available_dates",
    "description": "Check available appointment dates.",
    "parameters": {
        "type": "object",
        "properties": {"service_type": {"type": "string"}},
        "required": [],
    },
}


async def check_available_dates_executor(**kwargs: Any) -> dict[str, Any]:
    """Check available dates."""
    dates = []
    for i in range(1, 8):
        d = datetime.now(UTC) + timedelta(days=i)
        if d.weekday() < 5:  # Weekdays only
            dates.append({
                "date": d.strftime("%B %d, %Y"),
                "time_slots": ["8-10 AM", "10-12 PM", "1-3 PM", "3-5 PM"],
            })
    return {"success": True, "available_dates": dates[:5]}


schedule_appointment_schema: dict[str, Any] = {
    "name": "schedule_appointment",
    "description": "Schedule a service appointment.",
    "parameters": {
        "type": "object",
        "properties": {
            "date": {"type": "string"},
            "time_slot": {"type": "string"},
            "service_type": {"type": "string"},
        },
        "required": ["date", "time_slot"],
    },
}


async def schedule_appointment_executor(**kwargs: Any) -> dict[str, Any]:
    """Schedule appointment."""
    return {
        "success": True,
        "confirmation": f"APT{random.randint(100000, 999999)}",
        "date": kwargs.get("date"),
        "time_slot": kwargs.get("time_slot"),
        "service_type": kwargs.get("service_type", "General Service"),
    }


reschedule_appointment_schema: dict[str, Any] = {
    "name": "reschedule_appointment",
    "description": "Reschedule an existing appointment.",
    "parameters": {
        "type": "object",
        "properties": {
            "confirmation_number": {"type": "string"},
            "new_date": {"type": "string"},
            "new_time_slot": {"type": "string"},
        },
        "required": ["confirmation_number", "new_date"],
    },
}


async def reschedule_appointment_executor(**kwargs: Any) -> dict[str, Any]:
    """Reschedule appointment."""
    return {
        "success": True,
        "new_confirmation": f"APT{random.randint(100000, 999999)}",
        "new_date": kwargs.get("new_date"),
        "new_time_slot": kwargs.get("new_time_slot", "8-10 AM"),
    }


cancel_appointment_schema: dict[str, Any] = {
    "name": "cancel_appointment",
    "description": "Cancel a scheduled appointment.",
    "parameters": {
        "type": "object",
        "properties": {"confirmation_number": {"type": "string"}},
        "required": ["confirmation_number"],
    },
}


async def cancel_appointment_executor(**kwargs: Any) -> dict[str, Any]:
    """Cancel appointment."""
    return {
        "success": True,
        "cancelled": True,
        "confirmation_number": kwargs.get("confirmation_number"),
    }


verify_service_address_schema: dict[str, Any] = {
    "name": "verify_service_address",
    "description": "Verify if an address is in the service territory.",
    "parameters": {
        "type": "object",
        "properties": {"address": {"type": "string"}},
        "required": ["address"],
    },
}


async def verify_service_address_executor(**kwargs: Any) -> dict[str, Any]:
    """Verify service address."""
    return {
        "success": True,
        "serviceable": True,
        "address": kwargs.get("address"),
        "service_types_available": ["Electric", "Gas"],
    }


check_service_availability_schema: dict[str, Any] = {
    "name": "check_service_availability",
    "description": "Check what services are available at an address.",
    "parameters": {
        "type": "object",
        "properties": {"address": {"type": "string"}},
        "required": ["address"],
    },
}


async def check_service_availability_executor(**kwargs: Any) -> dict[str, Any]:
    """Check service availability."""
    return {
        "success": True,
        "address": kwargs.get("address"),
        "electric": True,
        "gas": True,
        "water": False,
        "message": "Electric and gas service available. Water service is provided by the city.",
    }


get_deposit_requirement_schema: dict[str, Any] = {
    "name": "get_deposit_requirement",
    "description": "Check deposit requirements for new service.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def get_deposit_requirement_executor(**kwargs: Any) -> dict[str, Any]:
    """Get deposit requirement."""
    required = random.random() > 0.5
    return {
        "success": True,
        "deposit_required": required,
        "deposit_amount": 150.00 if required else 0,
        "waiver_options": ["Good credit", "Letter of credit from previous utility"] if required else [],
    }


update_contact_info_schema: dict[str, Any] = {
    "name": "update_contact_info",
    "description": "Update contact information for the account.",
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": [],
    },
}


async def update_contact_info_executor(**kwargs: Any) -> dict[str, Any]:
    """Update contact info."""
    return {
        "success": True,
        "updated_fields": [k for k in ["phone", "email"] if kwargs.get(k)],
        "message": "Contact information updated successfully.",
    }


add_authorized_user_schema: dict[str, Any] = {
    "name": "add_authorized_user",
    "description": "Add an authorized user to the account.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "relationship": {"type": "string"},
        },
        "required": ["name"],
    },
}


async def add_authorized_user_executor(**kwargs: Any) -> dict[str, Any]:
    """Add authorized user."""
    return {
        "success": True,
        "authorized_user_added": kwargs.get("name"),
        "permissions": "Full account access",
    }


enroll_paperless_schema: dict[str, Any] = {
    "name": "enroll_paperless",
    "description": "Enroll in paperless billing.",
    "parameters": {
        "type": "object",
        "properties": {"email": {"type": "string"}},
        "required": [],
    },
}


async def enroll_paperless_executor(**kwargs: Any) -> dict[str, Any]:
    """Enroll in paperless billing."""
    return {
        "success": True,
        "enrolled": True,
        "monthly_savings": 2.00,
        "message": "Enrolled in paperless billing. You'll receive bills via email.",
    }


enroll_autopay_schema: dict[str, Any] = {
    "name": "enroll_autopay",
    "description": "Enroll in automatic payment (autopay) for the account.",
    "parameters": {
        "type": "object",
        "properties": {
            "payment_method": {"type": "string", "enum": ["bank_account", "credit_card", "debit_card"]},
            "payment_day": {"type": "integer", "description": "Day of month for payment (1-28)"},
        },
        "required": ["payment_method"],
    },
}


async def enroll_autopay_executor(**kwargs: Any) -> dict[str, Any]:
    """Enroll in automatic payment."""
    method = kwargs.get("payment_method", "bank_account")
    day = kwargs.get("payment_day", 15)
    return {
        "success": True,
        "enrolled": True,
        "payment_method": method,
        "payment_day": day,
        "message": f"Successfully enrolled in autopay. Payments will be processed on day {day} of each billing cycle using your {method.replace('_', ' ')}.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE EXTENDED TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

get_usage_comparison_schema: dict[str, Any] = {
    "name": "get_usage_comparison",
    "description": "Compare current usage to previous periods.",
    "parameters": {
        "type": "object",
        "properties": {"comparison_period": {"type": "string", "enum": ["last_month", "last_year", "same_month_last_year"]}},
        "required": [],
    },
}


async def get_usage_comparison_executor(**kwargs: Any) -> dict[str, Any]:
    """Get usage comparison."""
    current = random.randint(400, 800)
    comparison = random.randint(350, 850)
    diff = current - comparison
    return {
        "success": True,
        "current_usage_kwh": current,
        "comparison_usage_kwh": comparison,
        "difference_kwh": diff,
        "difference_percent": round((diff / comparison) * 100, 1),
        "trend": "higher" if diff > 0 else "lower",
    }


get_usage_breakdown_schema: dict[str, Any] = {
    "name": "get_usage_breakdown",
    "description": "Get a breakdown of usage by category.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def get_usage_breakdown_executor(**kwargs: Any) -> dict[str, Any]:
    """Get usage breakdown."""
    return {
        "success": True,
        "breakdown": [
            {"category": "Heating/Cooling", "percent": 45, "kwh": 360},
            {"category": "Water Heating", "percent": 18, "kwh": 144},
            {"category": "Appliances", "percent": 20, "kwh": 160},
            {"category": "Lighting", "percent": 10, "kwh": 80},
            {"category": "Other", "percent": 7, "kwh": 56},
        ],
        "total_kwh": 800,
    }


compare_to_neighbors_schema: dict[str, Any] = {
    "name": "compare_to_neighbors",
    "description": "Compare usage to similar homes in the area.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def compare_to_neighbors_executor(**kwargs: Any) -> dict[str, Any]:
    """Compare to neighbors."""
    your_usage = random.randint(500, 900)
    avg_similar = random.randint(600, 800)
    efficient = random.randint(400, 550)
    return {
        "success": True,
        "your_usage_kwh": your_usage,
        "similar_homes_avg_kwh": avg_similar,
        "most_efficient_kwh": efficient,
        "ranking": random.choice(["More efficient than 60% of similar homes", "Average for your area", "Using 15% more than similar homes"]),
    }


get_meter_info_schema: dict[str, Any] = {
    "name": "get_meter_info",
    "description": "Get meter information.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def get_meter_info_executor(**kwargs: Any) -> dict[str, Any]:
    """Get meter info."""
    return {
        "success": True,
        "meter_number": f"MTR{random.randint(100000, 999999)}",
        "meter_type": "Smart Meter",
        "last_read_date": (datetime.now(UTC) - timedelta(days=random.randint(1, 5))).strftime("%B %d, %Y"),
        "last_read_kwh": random.randint(45000, 50000),
    }


submit_meter_read_schema: dict[str, Any] = {
    "name": "submit_meter_read",
    "description": "Submit a customer meter reading.",
    "parameters": {
        "type": "object",
        "properties": {"reading": {"type": "number"}},
        "required": ["reading"],
    },
}


async def submit_meter_read_executor(**kwargs: Any) -> dict[str, Any]:
    """Submit meter read."""
    return {
        "success": True,
        "reading_submitted": kwargs.get("reading"),
        "confirmation": f"MRD{random.randint(100000, 999999)}",
        "message": "Thank you for submitting your meter reading.",
    }


request_meter_test_schema: dict[str, Any] = {
    "name": "request_meter_test",
    "description": "Request a meter accuracy test.",
    "parameters": {
        "type": "object",
        "properties": {"reason": {"type": "string"}},
        "required": [],
    },
}


async def request_meter_test_executor(**kwargs: Any) -> dict[str, Any]:
    """Request meter test."""
    return {
        "success": True,
        "request_id": f"MT{random.randint(100000, 999999)}",
        "fee": 25.00,
        "fee_refund": "Fee refunded if meter is found to be inaccurate",
        "estimated_date": (datetime.now(UTC) + timedelta(days=7)).strftime("%B %d, %Y"),
    }


explain_meter_reading_schema: dict[str, Any] = {
    "name": "explain_meter_reading",
    "description": "Explain how to read the meter.",
    "parameters": {
        "type": "object",
        "properties": {"meter_type": {"type": "string"}},
        "required": [],
    },
}


async def explain_meter_reading_executor(**kwargs: Any) -> dict[str, Any]:
    """Explain meter reading."""
    return {
        "success": True,
        "instructions": "For digital meters, simply read the numbers displayed. For analog meters, read each dial from left to right, recording the number each pointer has just passed.",
        "video_link": "https://example.com/meter-reading-guide",
    }


calculate_appliance_cost_schema: dict[str, Any] = {
    "name": "calculate_appliance_cost",
    "description": "Calculate the energy cost of a specific appliance.",
    "parameters": {
        "type": "object",
        "properties": {
            "appliance": {"type": "string"},
            "hours_per_day": {"type": "number"},
        },
        "required": ["appliance"],
    },
}


async def calculate_appliance_cost_executor(**kwargs: Any) -> dict[str, Any]:
    """Calculate appliance cost."""
    appliance = kwargs.get("appliance", "refrigerator")
    hours = kwargs.get("hours_per_day", 24)
    wattages = {
        "refrigerator": 150,
        "air_conditioner": 3000,
        "washing_machine": 500,
        "dryer": 3000,
        "dishwasher": 1800,
        "tv": 100,
    }
    watts = wattages.get(appliance.lower(), 500)
    kwh_per_day = (watts * hours) / 1000
    monthly_cost = kwh_per_day * 30 * 0.12
    return {
        "success": True,
        "appliance": appliance,
        "estimated_watts": watts,
        "kwh_per_day": round(kwh_per_day, 2),
        "monthly_cost": round(monthly_cost, 2),
    }


get_rebate_programs_schema: dict[str, Any] = {
    "name": "get_rebate_programs",
    "description": "Get available rebate programs.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}


async def get_rebate_programs_executor(**kwargs: Any) -> dict[str, Any]:
    """Get rebate programs."""
    return {
        "success": True,
        "programs": [
            {"name": "Smart Thermostat Rebate", "amount": 75, "description": "Rebate for ENERGY STAR thermostats"},
            {"name": "LED Lighting", "amount": 5, "description": "Per qualifying LED bulb"},
            {"name": "HVAC Upgrade", "amount": 300, "description": "For qualifying high-efficiency systems"},
            {"name": "Heat Pump Water Heater", "amount": 500, "description": "For heat pump water heaters"},
        ],
    }


schedule_energy_audit_schema: dict[str, Any] = {
    "name": "schedule_energy_audit",
    "description": "Schedule a home energy audit.",
    "parameters": {
        "type": "object",
        "properties": {"preferred_date": {"type": "string"}},
        "required": [],
    },
}


async def schedule_energy_audit_executor(**kwargs: Any) -> dict[str, Any]:
    """Schedule energy audit."""
    return {
        "success": True,
        "confirmation": f"EA{random.randint(100000, 999999)}",
        "scheduled_date": kwargs.get("preferred_date", (datetime.now(UTC) + timedelta(days=7)).strftime("%B %d, %Y")),
        "duration": "2-3 hours",
        "cost": "Free",
    }


enroll_time_of_use_schema: dict[str, Any] = {
    "name": "enroll_time_of_use",
    "description": "Enroll in time-of-use rate plan.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def enroll_time_of_use_executor(**kwargs: Any) -> dict[str, Any]:
    """Enroll in time-of-use."""
    return {
        "success": True,
        "enrolled": True,
        "rate_schedule": "Time-of-Use Residential",
        "peak_hours": "2 PM - 7 PM weekdays",
        "off_peak_savings": "Up to 30% savings during off-peak hours",
        "start_date": (datetime.now(UTC) + timedelta(days=30)).strftime("%B %d, %Y"),
    }


enroll_demand_response_schema: dict[str, Any] = {
    "name": "enroll_demand_response",
    "description": "Enroll in demand response program.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def enroll_demand_response_executor(**kwargs: Any) -> dict[str, Any]:
    """Enroll in demand response."""
    return {
        "success": True,
        "enrolled": True,
        "program": "Peak Time Rewards",
        "incentive": "$5 bill credit per event participation",
        "events_per_year": "Up to 15 events",
    }


check_solar_eligibility_schema: dict[str, Any] = {
    "name": "check_solar_eligibility",
    "description": "Check eligibility for solar programs.",
    "parameters": {
        "type": "object",
        "properties": {"service_address": {"type": "string"}},
        "required": [],
    },
}


async def check_solar_eligibility_executor(**kwargs: Any) -> dict[str, Any]:
    """Check solar eligibility."""
    return {
        "success": True,
        "eligible_for_net_metering": True,
        "community_solar_available": True,
        "estimated_savings": "$50-100/month with typical installation",
        "incentives_available": ["Federal Tax Credit 30%", "State Rebate $500/kW"],
    }


get_rate_schedule_schema: dict[str, Any] = {
    "name": "get_rate_schedule",
    "description": "Get the current rate schedule.",
    "parameters": {
        "type": "object",
        "properties": {"account_number": {"type": "string"}},
        "required": [],
    },
}


async def get_rate_schedule_executor(**kwargs: Any) -> dict[str, Any]:
    """Get rate schedule."""
    return {
        "success": True,
        "rate_schedule": "Residential Standard",
        "rates": {
            "energy_charge": "$0.12/kWh",
            "base_charge": "$12.50/month",
            "fuel_adjustment": "$0.02/kWh",
        },
        "available_rate_schedules": ["Residential Standard", "Time-of-Use", "EV Rate"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# OMNICHANNEL & ESCALATION TOOLS
# ═══════════════════════════════════════════════════════════════════════════════
# Note: check_queue_status, offer_channel_switch, and execute_channel_handoff
# are registered in channel_handoff.py (imported first in registry.py).
# Those versions include proper is_handoff=True flags and full implementation.


escalate_human_schema: dict[str, Any] = {
    "name": "escalate_human",
    "description": "Escalate to a human agent.",
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {"type": "string"},
            "priority": {"type": "string", "enum": ["normal", "high", "urgent"]},
        },
        "required": [],
    },
}


async def escalate_human_executor(**kwargs: Any) -> dict[str, Any]:
    """Escalate to human agent."""
    priority = kwargs.get("priority", "normal")
    wait_times = {"normal": random.randint(5, 15), "high": random.randint(2, 8), "urgent": random.randint(1, 3)}
    return {
        "success": True,
        "escalation_initiated": True,
        "priority": priority,
        "estimated_wait_minutes": wait_times.get(priority, 10),
        "ticket_number": f"ESC{random.randint(100000, 999999)}",
    }


schedule_callback_schema: dict[str, Any] = {
    "name": "schedule_callback",
    "description": "Schedule a callback from a human agent.",
    "parameters": {
        "type": "object",
        "properties": {
            "preferred_time": {"type": "string"},
            "phone_number": {"type": "string"},
        },
        "required": [],
    },
}


async def schedule_callback_executor(**kwargs: Any) -> dict[str, Any]:
    """Schedule callback."""
    return {
        "success": True,
        "callback_scheduled": True,
        "scheduled_time": kwargs.get("preferred_time", "Within 2 hours"),
        "confirmation": f"CB{random.randint(100000, 999999)}",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

def register_extended_utilities_tools() -> None:
    """Register all extended utilities tools."""
    
    # Identity & Account
    register_tool("verify_customer_identity", verify_customer_identity_schema, verify_customer_identity_executor, tags={"utilities", "account"})
    register_tool("get_account_info", get_account_info_schema, get_account_info_executor, tags={"utilities", "account"})
    register_tool("get_service_address", get_service_address_schema, get_service_address_executor, tags={"utilities", "account"})
    register_tool("get_payment_status", get_payment_status_schema, get_payment_status_executor, tags={"utilities", "account", "billing"})
    
    # Billing Extended
    register_tool("get_bill_history", get_bill_history_schema, get_bill_history_executor, tags={"utilities", "billing"})
    register_tool("explain_charges", explain_charges_schema, explain_charges_executor, tags={"utilities", "billing"})
    register_tool("get_payment_history", get_payment_history_schema, get_payment_history_executor, tags={"utilities", "billing"})
    register_tool("setup_autopay", setup_autopay_schema, setup_autopay_executor, tags={"utilities", "billing"})
    register_tool("apply_credit", apply_credit_schema, apply_credit_executor, tags={"utilities", "billing"})
    register_tool("request_bill_review", request_bill_review_schema, request_bill_review_executor, tags={"utilities", "billing"})
    register_tool("check_eligible_credits", check_eligible_credits_schema, check_eligible_credits_executor, tags={"utilities", "billing"})
    register_tool("update_billing_address", update_billing_address_schema, update_billing_address_executor, tags={"utilities", "billing"})
    register_tool("check_assistance_programs", check_assistance_programs_schema, check_assistance_programs_executor, tags={"utilities", "billing"})
    register_tool("enroll_budget_billing", enroll_budget_billing_schema, enroll_budget_billing_executor, tags={"utilities", "billing"})
    
    # Outage Extended
    register_tool("get_restoration_eta", get_restoration_eta_schema, get_restoration_eta_executor, tags={"utilities", "outage"})
    register_tool("get_outage_map", get_outage_map_schema, get_outage_map_executor, tags={"utilities", "outage"})
    register_tool("subscribe_outage_updates", subscribe_outage_updates_schema, subscribe_outage_updates_executor, tags={"utilities", "outage"})
    register_tool("get_emergency_contacts", get_emergency_contacts_schema, get_emergency_contacts_executor, tags={"utilities", "outage", "emergency"})
    register_tool("check_outage_credits", check_outage_credits_schema, check_outage_credits_executor, tags={"utilities", "outage", "billing"})
    register_tool("request_outage_credit", request_outage_credit_schema, request_outage_credit_executor, tags={"utilities", "outage", "billing"})
    register_tool("report_gas_leak", report_gas_leak_schema, report_gas_leak_executor, tags={"utilities", "outage", "emergency"})
    
    # Service Extended
    register_tool("start_new_service", start_new_service_schema, start_new_service_executor, tags={"utilities", "service"})
    register_tool("stop_service", stop_service_schema, stop_service_executor, tags={"utilities", "service"})
    register_tool("schedule_meter_read", schedule_meter_read_schema, schedule_meter_read_executor, tags={"utilities", "service"})
    register_tool("check_available_dates", check_available_dates_schema, check_available_dates_executor, tags={"utilities", "service"})
    register_tool("schedule_appointment", schedule_appointment_schema, schedule_appointment_executor, tags={"utilities", "service"})
    register_tool("reschedule_appointment", reschedule_appointment_schema, reschedule_appointment_executor, tags={"utilities", "service"})
    register_tool("cancel_appointment", cancel_appointment_schema, cancel_appointment_executor, tags={"utilities", "service"})
    register_tool("verify_service_address", verify_service_address_schema, verify_service_address_executor, tags={"utilities", "service"})
    register_tool("check_service_availability", check_service_availability_schema, check_service_availability_executor, tags={"utilities", "service"})
    register_tool("get_deposit_requirement", get_deposit_requirement_schema, get_deposit_requirement_executor, tags={"utilities", "service"})
    register_tool("update_contact_info", update_contact_info_schema, update_contact_info_executor, tags={"utilities", "service", "account"})
    register_tool("add_authorized_user", add_authorized_user_schema, add_authorized_user_executor, tags={"utilities", "service", "account"})
    register_tool("enroll_paperless", enroll_paperless_schema, enroll_paperless_executor, tags={"utilities", "service", "billing"})
    register_tool("enroll_autopay", enroll_autopay_schema, enroll_autopay_executor, tags={"utilities", "service", "billing"})
    
    # Usage Extended
    register_tool("get_usage_comparison", get_usage_comparison_schema, get_usage_comparison_executor, tags={"utilities", "usage"})
    register_tool("get_usage_breakdown", get_usage_breakdown_schema, get_usage_breakdown_executor, tags={"utilities", "usage"})
    register_tool("compare_to_neighbors", compare_to_neighbors_schema, compare_to_neighbors_executor, tags={"utilities", "usage"})
    register_tool("get_meter_info", get_meter_info_schema, get_meter_info_executor, tags={"utilities", "usage"})
    register_tool("submit_meter_read", submit_meter_read_schema, submit_meter_read_executor, tags={"utilities", "usage"})
    register_tool("request_meter_test", request_meter_test_schema, request_meter_test_executor, tags={"utilities", "usage"})
    register_tool("explain_meter_reading", explain_meter_reading_schema, explain_meter_reading_executor, tags={"utilities", "usage"})
    register_tool("calculate_appliance_cost", calculate_appliance_cost_schema, calculate_appliance_cost_executor, tags={"utilities", "usage"})
    register_tool("get_rebate_programs", get_rebate_programs_schema, get_rebate_programs_executor, tags={"utilities", "usage"})
    register_tool("schedule_energy_audit", schedule_energy_audit_schema, schedule_energy_audit_executor, tags={"utilities", "usage"})
    register_tool("enroll_time_of_use", enroll_time_of_use_schema, enroll_time_of_use_executor, tags={"utilities", "usage"})
    register_tool("enroll_demand_response", enroll_demand_response_schema, enroll_demand_response_executor, tags={"utilities", "usage"})
    register_tool("check_solar_eligibility", check_solar_eligibility_schema, check_solar_eligibility_executor, tags={"utilities", "usage"})
    register_tool("get_rate_schedule", get_rate_schedule_schema, get_rate_schedule_executor, tags={"utilities", "usage"})
    
    # Escalation tools (Omnichannel tools are in channel_handoff.py)
    register_tool("escalate_human", escalate_human_schema, escalate_human_executor, tags={"utilities", "escalation"})
    register_tool("schedule_callback", schedule_callback_schema, schedule_callback_executor, tags={"utilities", "escalation"})
    
    logger.info("Extended utilities tools registered: %d tools", 47)  # 50 - 3 omnichannel


# Auto-register on import
register_extended_utilities_tools()
