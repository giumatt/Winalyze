variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "westeurope"
}

variable "storage_account_name" {
  description = "Unique name for the Azure Storage Account"
  type        = string
  default     = "winalyzestorage"
}