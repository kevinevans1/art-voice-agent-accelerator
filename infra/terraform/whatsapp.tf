# ============================================================================
# WHATSAPP CHANNEL INTEGRATION
# ============================================================================
# This file configures Event Grid subscriptions for WhatsApp messaging
# via Azure Communication Services Advanced Messaging.
#
# Prerequisites:
#   1. ACS resource deployed (communication.tf)
#   2. WhatsApp Business Account connected to ACS via Azure Portal
#   3. Backend Container App deployed (containers.tf)
#
# Usage:
#   Set enable_whatsapp = true and provide whatsapp_channel_id
# ============================================================================

# ============================================================================
# EVENT GRID SYSTEM TOPIC FOR ACS
# ============================================================================
# Creates a system topic to receive events from Azure Communication Services.
# This is used for WhatsApp message delivery events.

resource "azurerm_eventgrid_system_topic" "acs_messaging" {
  count = var.enable_whatsapp ? 1 : 0

  name                   = "evgt-acs-messaging-${local.resource_token}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = "global"
  source_arm_resource_id = azapi_resource.acs.id
  topic_type             = "Microsoft.Communication.CommunicationServices"

  tags = local.tags
}

# ============================================================================
# WHATSAPP MESSAGE SUBSCRIPTION
# ============================================================================
# Subscribes to WhatsApp message events and delivers them to the backend webhook.

resource "azurerm_eventgrid_system_topic_event_subscription" "whatsapp_messages" {
  count = var.enable_whatsapp ? 1 : 0

  name                = "whatsapp-messages-${local.resource_token}"
  system_topic        = azurerm_eventgrid_system_topic.acs_messaging[0].name
  resource_group_name = azurerm_resource_group.main.name

  # Event types for WhatsApp Advanced Messaging
  included_event_types = [
    "Microsoft.Communication.AdvancedMessageReceived",
    "Microsoft.Communication.AdvancedMessageDeliveryStatusUpdated",
  ]

  # Webhook endpoint on the backend container app
  webhook_endpoint {
    url                               = "https://${azurerm_container_app.backend.latest_revision_fqdn}/api/v1/channels/whatsapp/webhook"
    max_events_per_batch              = 1
    preferred_batch_size_in_kilobytes = 64
  }

  # Retry policy for failed deliveries
  retry_policy {
    max_delivery_attempts = 30
    event_time_to_live    = 1440 # 24 hours in minutes
  }

  depends_on = [
    azurerm_container_app.backend,
    azapi_resource.acs,
  ]
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "whatsapp_webhook_url" {
  description = "WhatsApp webhook URL for Event Grid subscription"
  value       = var.enable_whatsapp ? "https://${azurerm_container_app.backend.latest_revision_fqdn}/api/v1/channels/whatsapp/webhook" : null
}

output "whatsapp_event_subscription_id" {
  description = "WhatsApp Event Grid subscription ID"
  value       = var.enable_whatsapp ? azurerm_eventgrid_system_topic_event_subscription.whatsapp_messages[0].id : null
}
