# ============================================================================
# WEBCHAT DEMO CONTAINER APP
# ============================================================================
# Deploys the standalone WebChat demo application for omnichannel demonstrations.
# This is a separate frontend that connects to the same backend, demonstrating
# how different channels can share customer context.
#
# Usage:
#   Set enable_webchat_demo = true to deploy
# ============================================================================

resource "azurerm_container_app" "webchat_demo" {
  count = var.enable_webchat_demo ? 1 : 0

  name                         = "webchat-demo-${local.resource_token}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  tags = local.tags

  # Image is managed outside of terraform (i.e azd deploy)
  lifecycle {
    ignore_changes = [
      template[0].container[0].image,
    ]
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "webchat-demo"
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "BACKEND_URL"
        value = "https://${azurerm_container_app.backend.latest_revision_fqdn}"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 3001

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.backend.id
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.backend.id]
  }

  depends_on = [
    azurerm_container_app.backend,
    azurerm_role_assignment.acr_backend_pull,
  ]
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "webchat_demo_url" {
  description = "WebChat demo application URL"
  value       = var.enable_webchat_demo ? "https://${azurerm_container_app.webchat_demo[0].latest_revision_fqdn}" : null
}

output "webchat_demo_fqdn" {
  description = "WebChat demo FQDN"
  value       = var.enable_webchat_demo ? azurerm_container_app.webchat_demo[0].latest_revision_fqdn : null
}
